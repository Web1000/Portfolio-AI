import json
import re
import math
from urllib.parse import quote as urlquote
import urllib.request

HEADERS = {"User-Agent": "Mozilla/5.0"}

CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    "?interval=1d&range=1y"
)

PRICE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"

NAME_TO_TICKER = {
    "nvidia": "NVDA", "apple": "AAPL", "microsoft": "MSFT",
    "amazon": "AMZN", "tesla": "TSLA", "meta": "META",
    "alphabet": "GOOGL", "google": "GOOGL",
    "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "solana": "SOL-USD",
}

IGNORE_SYMBOLS = {"ETF", "STOCK", "CRYPTO"}

def normalize_ticker(raw: str) -> str:
    """Turn user input like 'apple' or 'aapl' into a Yahoo Finance symbol."""
    cleaned = raw.strip()
    lowered = cleaned.lower()
    if lowered in NAME_TO_TICKER:
        return NAME_TO_TICKER[lowered]
    ticker = cleaned.upper()
    if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.\-^=]{0,14}", ticker):
        raise ValueError("Enter a valid ticker, such as AAPL or BRK-B.")
    return ticker

def fetch_ohlcv(ticker: str) -> dict | None:
    """Fetch one year of daily bars, dropping incomplete or invalid records."""
    url = CHART_URL.format(ticker=urlquote(normalize_ticker(ticker), safe=""))
    try:

        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.load(resp)
    except Exception:
        return None

    result = payload.get("chart", {}).get("result")
    if not result:
        return None

    chart = result[0]
    timestamps = chart.get("timestamp", [])
    quote = (chart.get("indicators", {}).get("quote") or [{}])[0]

    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    if not timestamps or not closes:
        return None

    clean_ts, clean_o, clean_h, clean_l, clean_c, clean_v = [], [], [], [], [], []
    for i in range(len(timestamps)):
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        v = volumes[i] if i < len(volumes) else None
        if all(isinstance(x, (int, float)) and math.isfinite(x) and x > 0 for x in (o, h, l, c)):
            clean_ts.append(timestamps[i])
            clean_o.append(float(o))
            clean_h.append(float(h))
            clean_l.append(float(l))
            clean_c.append(float(c))
            clean_v.append(int(v) if isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 else 0)

    if len(clean_c) < 20:
        return None

    return {
        "ticker": ticker,
        "timestamps": clean_ts,
        "opens": clean_o,
        "highs": clean_h,
        "lows": clean_l,
        "closes": clean_c,
        "volumes": clean_v,
    }

def _guess_ticker(question: str, topic: str) -> str | None:
    lowered = question.lower()
    for name, ticker in NAME_TO_TICKER.items():
        if re.search(r"\b" + re.escape(name) + r"\b", lowered):
            return ticker
    matches = re.findall(r"\b[A-Z]{2,5}(?:-USD)?\b", question)
    if matches:
        for match in matches:
            if match not in IGNORE_SYMBOLS:
                return match
    return None

def get_market_snapshot(question: str, topic: str) -> dict | None:
    """Retrieve a recent price snapshot for an explicitly identified instrument."""
    ticker = _guess_ticker(question, topic)
    if not ticker:
        return None
    try:
        req = urllib.request.Request(PRICE_URL.format(ticker=urlquote(normalize_ticker(ticker), safe="")), headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.load(resp)
    except Exception:
        return None

    results = payload.get("chart", {}).get("result")
    if not results:
        return None
    result = results[0]
    closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close", [])
    closes = [float(c) for c in closes if isinstance(c, (float, int)) and math.isfinite(c) and c > 0]
    if len(closes) < 2:
        return None

    current = closes[-1]
    previous = closes[-2]
    change_pct = ((current - previous) / previous) * 100
    five_day_pct = ((current - closes[0]) / closes[0]) * 100

    return {
        "ticker": ticker,
        "price": round(current, 2),
        "daily_change_pct": round(change_pct, 2),
        "window_change_pct": round(five_day_pct, 2),
        "currency": result.get("meta", {}).get("currency", "unknown"),
        "source_url": f"https://finance.yahoo.com/quote/{urlquote(ticker)}/",
    }
