"""SEC annual facts, aligned to one fiscal year; missing facts stay missing."""
from datetime import date, datetime, timezone
import json
import math
import os
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.data_access.market_data import HEADERS, normalize_ticker


def _get_json(url: str, *, sec: bool = True) -> dict:
    headers = HEADERS
    if sec:
        identity = os.environ.get("SEC_USER_AGENT", "").strip()
        if not identity or "@" not in identity or "example.com" in identity:
            raise ValueError("Set SEC_USER_AGENT to your application name and contact email.")
        headers = {"User-Agent": identity, "Accept": "application/json"}
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def annual_fact(facts: dict, concepts: list[str], unit: str, *, end: str | None = None,
                duration: bool = False) -> dict | None:
    """Prefer the newest fiscal period, then concept priority and latest amendment.

    Annual duration metrics must span 330–380 days; quarterly comparative entries
    inside a 10-K are excluded. Instant facts must match the selected fiscal end.
    """
    candidates = []
    for priority, concept in enumerate(concepts):
        namespace = "dei" if concept == "EntityCommonStockSharesOutstanding" else "us-gaap"
        records = facts.get("facts", {}).get(namespace, {}).get(concept, {}).get("units", {}).get(unit, [])
        for item in records:
            value = item.get("val")
            if item.get("form") not in ("10-K", "10-K/A") or not isinstance(value, (int, float)) or not math.isfinite(value):
                continue
            if not item.get("end") or (end and item["end"] != end):
                continue
            if duration:
                try:
                    days = (date.fromisoformat(item["end"]) - date.fromisoformat(item["start"])).days
                except (KeyError, ValueError):
                    continue
                if not 330 <= days <= 380:
                    continue
            candidates.append({**item, "concept": concept, "priority": priority})
    return max(candidates, key=lambda x: (x["end"], -x["priority"], x.get("filed", ""))) if candidates else None


def extract_financials(facts: dict) -> dict:
    ocf = annual_fact(facts, ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"], "USD", duration=True)
    if not ocf:
        raise ValueError("No supported annual operating cash flow found in SEC filings.")
    end = ocf["end"]
    capex = annual_fact(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"], "USD", end=end, duration=True)
    shares = annual_fact(facts, ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"], "shares", end=end)
    # Use an aggregate only when explicitly reported; never silently treat missing debt as zero.
    debt = annual_fact(facts, ["LongTermDebtCurrent", "LongTermDebtAndFinanceLeaseObligationsCurrent"], "USD", end=end)
    noncurrent = annual_fact(facts, ["LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"], "USD", end=end)
    total = annual_fact(facts, ["LongTermDebt", "LongTermDebtAndFinanceLeaseObligations"], "USD", end=end)
    short = annual_fact(facts, ["ShortTermBorrowings", "ShortTermDebtCurrent"], "USD", end=end)
    debt_value = float(total["val"]) if total else (
        float(debt["val"] + noncurrent["val"]) if debt and noncurrent else None
    )
    warnings = []
    if debt_value is not None and short:
        debt_value += float(short["val"])
    if not short:
        warnings.append("Separate short-term borrowing data is unavailable; the debt measure may be incomplete.")
    fields = {"operating_cash_flow": float(ocf["val"]), "capex": float(capex["val"]) if capex else None,
              "shares": float(shares["val"]) if shares else None, "debt": debt_value}
    for key, value in fields.items():
        if value is None:
            warnings.append(f"Missing comparable annual {key.replace('_', ' ')} data.")
    return {**fields, "period_end": end, "filed": ocf.get("filed"), "warnings": warnings}


def fetch_fundamentals(ticker: str) -> dict:
    ticker = normalize_ticker(ticker).replace(".", "-")
    companies = _get_json("https://www.sec.gov/files/company_tickers.json")
    company = next((c for c in companies.values() if c["ticker"] == ticker), None)
    if not company:
        raise ValueError("No SEC company found for this ticker. Use a US filing company.")
    cik = str(company["cik_str"]).zfill(10)
    facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    profile = _get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
    financials = extract_financials(_get_json(facts_url))
    payload = _get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}?interval=1d&range=5d", sec=False)
    results = payload.get("chart", {}).get("result") or []
    price, as_of = None, None
    if results:
        chart = results[0]
        if chart.get("meta", {}).get("currency") != "USD":
            raise ValueError("Value analysis requires a USD stock quote.")
        closes = (chart.get("indicators", {}).get("quote") or [{}])[0].get("close", [])
        for timestamp, close in zip(chart.get("timestamp", []), closes):
            if isinstance(close, (float, int)) and math.isfinite(close) and close > 0:
                price = float(close)
                as_of = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
    if price is None:
        financials["warnings"].append("Market price is unavailable; valuation comparison is disabled.")
    return {**financials, "ticker": ticker, "company_name": company["title"],
            "profile": {k: profile.get(k) for k in ("name", "sicDescription", "exchanges", "tickers")},
            "current_price": price, "price_as_of": as_of,
            "sources": [{"title": "SEC company facts", "url": facts_url},
                        {"title": "Yahoo Finance quote", "url": f"https://finance.yahoo.com/quote/{quote(ticker)}/"}]}
