"""Value-investing workflow: annual evidence → arithmetic → narrative → report."""
import json
from typing import TypedDict

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.core.llm import structured
from src.data_access.demo import fundamentals
from src.data_access.sec_edgar import fetch_fundamentals

MULTIPLE = 12


class BusinessReport(BaseModel):
    business_summary: str = Field(min_length=1, max_length=2500)
    moat_analysis: str = Field(min_length=1, max_length=2500)
    business_score: int = Field(ge=0, le=20)
    moat_score: int = Field(ge=0, le=25)


class ValueState(TypedDict):
    ticker: str
    data: dict
    metrics: dict
    narrative: dict
    report: dict
    trace: list[dict]


def trace(state, name, detail):
    return state["trace"] + [{"name": name, "detail": detail, "status": "done"}]


def calculate(data: dict) -> dict:
    ocf, capex, shares, debt, price = (data.get(k) for k in
        ("operating_cash_flow", "capex", "shares", "debt", "current_price"))
    earnings = ocf - capex if ocf is not None and capex is not None and capex >= 0 else None
    per_share = earnings / shares if earnings is not None and shares is not None and shares > 0 else None
    value = per_share * MULTIPLE if per_share is not None and per_share > 0 else None
    margin = (value - price) / value if value is not None and price is not None and price > 0 else None
    ratio = debt / earnings if debt is not None and debt >= 0 and earnings is not None and earnings > 0 else None
    conversion = earnings / ocf if earnings is not None and ocf is not None and ocf > 0 else None
    cash_score = None if earnings is None else 0
    if earnings is not None and earnings > 0 and conversion is not None:
        cash_score = next((score for threshold, score in [(0.45, 25), (.35, 22), (.25, 18), (.15, 12), (.05, 6)] if conversion >= threshold), 2)
    debt_score = None if debt is None else 0
    if ratio is not None:
        debt_score = next((score for threshold, score in [(.5, 15), (1, 11), (2, 7), (4, 3)] if ratio < threshold), 0)
    valuation_score = None if margin is None else next((score for threshold, score in [(.15, 15), (.12, 12), (.09, 9), (.06, 6), (.03, 3)] if margin >= threshold), 0)
    return {"owner_earnings_proxy": earnings, "owner_earnings_per_share": per_share,
            "value_per_share": value, "margin_of_safety": margin, "debt_to_earnings": ratio,
            "cash_flow_score": cash_score, "debt_score": debt_score, "valuation_score": valuation_score}


class ValueAgent:
    def __init__(self, demo: bool = True):
        self.demo = demo
        graph = StateGraph(ValueState)
        for name, node in [("evidence", self.evidence), ("calculations", self.calculations),
                           ("business_review", self.business_review), ("report", self.report)]:
            graph.add_node(name, node)
        graph.set_entry_point("evidence")
        graph.add_edge("evidence", "calculations")
        graph.add_edge("calculations", "business_review")
        graph.add_edge("business_review", "report")
        graph.add_edge("report", END)
        self.graph = graph.compile()

    def evidence(self, state):
        data = fundamentals() if self.demo else fetch_fundamentals(state["ticker"])
        return {"data": data, "trace": trace(state, "Annual evidence", f"Financial period ending {data['period_end']}.")}

    def calculations(self, state):
        return {"metrics": calculate(state["data"]), "trace": trace(state, "Financial calculations", "Cash flow, leverage, and per-share value calculated in Python.")}

    def business_review(self, state):
        if self.demo:
            narrative = {"business_summary": "Demo Software Co. is a fictional subscription software business. This prepared example illustrates recurring revenue; it is not a claim about a real company.",
                         "moat_analysis": "The example assumes customer switching costs. No independent moat evidence is supplied; the scores are illustrative fixtures.",
                         "business_score": 16, "moat_score": 14}
        else:
            narrative = structured(
                "Review this SEC profile. It provides identity and industry, not a full business description. "
                "Do not infer products, management quality or competitive advantages from the company name. "
                "Assign zero moat points when competitive evidence is absent. Scores are an educational rubric, "
                "not probabilities. State limitations explicitly.\n" + json.dumps(state["data"]["profile"]), BusinessReport)
        return {"narrative": narrative, "trace": trace(state, "Business review", "Prepared illustrative narrative." if self.demo else "Reviewed the supplied SEC profile with Claude.")}

    def report(self, state):
        data, metrics, narrative = state["data"], state["metrics"], state["narrative"]
        scores = {"Business understanding": [narrative["business_score"], 20],
                  "Cash flow": [metrics["cash_flow_score"], 25], "Moat evidence": [narrative["moat_score"], 25],
                  "Debt": [metrics["debt_score"], 15], "Valuation": [metrics["valuation_score"], 15]}
        incomplete = any(value[0] is None for value in scores.values())
        total = None if incomplete else sum(v[0] for v in scores.values())
        label = "Incomplete data" if incomplete else "Strong rubric score" if total >= 85 else "Watchlist" if total >= 70 else "Mixed" if total >= 50 else "Weak rubric score"
        margin = metrics["margin_of_safety"]
        valuation_note = "A positive per-share estimate and valid quote are required for comparison."
        if margin is not None:
            valuation_note = "The modeled margin of safety meets the 15% threshold." if margin >= .15 else "The modeled margin of safety is below the 15% threshold."
        report = {"ticker": data["ticker"], "company_name": data["company_name"], **metrics, **narrative,
                  "score": total, "scores": scores, "assessment": label, "valuation_note": valuation_note,
                  "current_price": data["current_price"], "period_end": data["period_end"], "filed": data.get("filed"),
                  "price_as_of": data["price_as_of"], "warnings": data["warnings"], "sources": data["sources"],
                  "method": "Operating cash flow less capex is a simplified owner-earnings proxy. Value per share = proxy / fiscal-end shares × 12. This is a heuristic, not a DCF or a price target."}
        return {"report": report, "trace": trace(state, "Report", "Assembled score breakdown, evidence, and limitations.")}

    def run(self, ticker):
        result = self.graph.invoke({"ticker": ticker, "data": {}, "metrics": {}, "narrative": {}, "report": {}, "trace": []})
        return {"report": result["report"], "trace": result["trace"]}
