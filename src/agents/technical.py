"""Deterministic indicators followed by a constrained narrative review."""
from datetime import datetime, timezone
import json
from typing import Literal, TypedDict
from urllib.parse import quote

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.agents.value import trace
from src.core.llm import structured
from src.core.signals import compute_signals
from src.data_access.demo import prices
from src.data_access.market_data import fetch_ohlcv


class TechnicalReport(BaseModel):
    verdict: Literal["bullish", "mixed", "neutral", "bearish"]
    summary: str = Field(min_length=1, max_length=2500)
    caution: str = Field(min_length=1, max_length=1500)
    watch_next: str = Field(min_length=1, max_length=1500)


class TechnicalState(TypedDict):
    ticker: str
    prices: dict
    signals: dict
    report: dict
    trace: list[dict]


class TechnicalAgent:
    def __init__(self, demo=True):
        self.demo = demo
        graph = StateGraph(TechnicalState)
        graph.add_node("prices", self.fetch)
        graph.add_node("signals", self.signals)
        graph.add_node("review", self.review)
        graph.set_entry_point("prices")
        graph.add_edge("prices", "signals")
        graph.add_edge("signals", "review")
        graph.add_edge("review", END)
        self.graph = graph.compile()

    def fetch(self, state):
        data = prices() if self.demo else fetch_ohlcv(state["ticker"])
        if not data:
            raise ValueError("Price history is unavailable. Try another ticker or use demo mode.")
        return {"prices": data, "trace": trace(state, "Price history", f"Loaded {len(data['closes'])} daily bars.")}

    def signals(self, state):
        return {"signals": compute_signals(state["prices"]), "trace": trace(state, "Signal engine", "Calculated moving averages, RSI, volatility, levels, and volume.")}

    def review(self, state):
        signals = state["signals"]
        if self.demo:
            report = {"verdict": "mixed", "summary": "This synthetic series illustrates a rising trend with periodic pullbacks. The computed indicators below show how recent momentum can differ from the longer trend.",
                      "caution": "Synthetic prices cannot establish predictive performance or investment suitability.",
                      "watch_next": "Compare the closing price with the two moving averages and the nearest observed pivot levels."}
        else:
            compact = json.loads(json.dumps(signals))
            compact["trend"].pop("ma20_series")
            compact["trend"].pop("ma50_series")
            report = structured("Explain conflicts and limitations in these precomputed indicators. Do not give allocation sizes, trade instructions or invented price targets.\n" + json.dumps(compact), TechnicalReport)
        return {"report": report, "trace": trace(state, "Technical review", "Added prepared demo commentary." if self.demo else "Interpreted the computed indicators with Claude.")}

    def run(self, ticker):
        result = self.graph.invoke({"ticker": ticker, "prices": {}, "signals": {}, "report": {}, "trace": []})
        as_of = datetime.fromtimestamp(result["prices"]["timestamps"][-1], timezone.utc).date().isoformat()
        return {"ticker": result["prices"]["ticker"], "price_data": result["prices"], "signals": result["signals"],
                "report": result["report"], "trace": result["trace"], "as_of": as_of,
                "sources": [] if self.demo else [{"title": "Yahoo Finance historical prices", "url": f"https://finance.yahoo.com/quote/{quote(ticker)}/history/"}]}
