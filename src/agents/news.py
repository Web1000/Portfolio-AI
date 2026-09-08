"""Question routing → evidence retrieval → explanation → plain-language rewrite."""
import re
from typing import TypedDict

from langgraph.graph import END, StateGraph

from src.agents.value import trace
from src.core.llm import generate
from src.data_access.market_data import get_market_snapshot
from src.data_access.news_feed import get_news


def classify(question: str) -> str:
    groups = {"crypto": ("bitcoin", "btc", "ethereum", "eth", "crypto", "token", "solana"),
              "etf": ("etfs?", "exchange.traded funds?", "index funds?", "spy", "qqq", "voo"),
              "beginner": ("what is", "how does", "explain", "beginner", "difference between")}
    for topic, patterns in groups.items():
        if any(re.search(r"\b" + pattern + r"\b", question, re.I) for pattern in patterns):
            return topic
    return "stock"


class NewsState(TypedDict):
    question: str
    topic: str
    context: str
    sources: list[dict]
    draft: str
    answer: str
    trace: list[dict]


class NewsAgent:
    def __init__(self, demo=True):
        self.demo = demo
        graph = StateGraph(NewsState)
        graph.add_node("classify", self.route)
        for topic in ("stock", "crypto", "etf", "beginner"):
            graph.add_node(topic, self.explain)
            graph.add_edge(topic, "simplify")
        graph.add_node("simplify", self.simplify)
        graph.set_entry_point("classify")
        graph.add_conditional_edges("classify", lambda state: state["topic"], {t: t for t in ("stock", "crypto", "etf", "beginner")})
        graph.add_edge("simplify", END)
        self.graph = graph.compile()

    def route(self, state):
        topic = classify(state["question"])
        return {"topic": topic, "trace": trace(state, "Question router", f"Selected the {topic} explanation branch.")}

    def explain(self, state):
        if self.demo:
            context = "Prepared educational example. No headlines or current market data were retrieved."
            sources = []
            draft = "An ETF holds a basket of assets and trades on an exchange. An index ETF aims to track a benchmark. Diversification reduces dependence on one company, but the fund can still lose value when its market falls. Compare holdings, fees, tracking differences, and concentration before researching a fund further."
        else:
            articles = get_news(state["question"], state["topic"], limit=5)
            snapshot = get_market_snapshot(state["question"], state["topic"])
            sources = [{"title": a["title"], "url": a["link"], "published": a["published"]} for a in articles]
            context = "\n".join(f"{a['title']} | {a['source']} | {a['published']} | {a['link']}" for a in articles)
            if snapshot:
                sources.append({"title": "Yahoo Finance price snapshot", "url": snapshot["source_url"]})
                context += f"\nRecent price snapshot (may be delayed): {snapshot}"
            context = context or "No external evidence was available. Do not assert a current price move or cause."
            draft = generate(f"Write a concise {state['topic']} explanation for this question: {state['question']}\nEvidence:\n{context}\nHeadlines are not full articles or proof of causation. Explain uncertainty and distinguish general concepts from recent claims. Preserve source URLs for any recent claims.")
        return {"context": context, "sources": sources, "draft": draft,
                "trace": trace(state, "Evidence and explanation", "Loaded the prepared ETF example." if self.demo else f"Retrieved {len(sources)} headlines and drafted an explanation.")}

    def simplify(self, state):
        answer = state["draft"] if self.demo else generate("Rewrite this draft in plain language. Preserve uncertainties and source URLs. Add no new facts.\n" + state["draft"])
        return {"answer": answer, "trace": trace(state, "Plain-language review", "Prepared the final explanation.")}

    def run(self, question):
        if self.demo:
            question = "What is an index ETF?"
        result = self.graph.invoke({"question": question, "topic": "", "context": "", "sources": [], "draft": "", "answer": "", "trace": []})
        return {key: result[key] for key in ("question", "topic", "context", "sources", "answer", "trace")}
