import math

def simple_moving_average(prices: list[float], window: int) -> list[float | None]:
    """Return a list the same length as prices with the rolling average."""
    if window < 1:
        raise ValueError("Window must be positive.")
    result = []
    for i in range(len(prices)):

        if i < window - 1:
            result.append(None)
        else:

            chunk = prices[i - window + 1: i + 1]
            average = sum(chunk) / window
            result.append(average)
    return result

def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Relative Strength Index using the last `period` price changes."""
    if period < 1:
        raise ValueError("Period must be positive.")
    if len(closes) < period + 1:
        return None

    changes = []
    for i in range(len(closes) - period, len(closes)):
        changes.append(closes[i] - closes[i - 1])

    gains = []
    losses = []
    for change in changes:
        if change > 0:
            gains.append(change)
        elif change < 0:
            losses.append(-change)

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 50.0 if avg_gain == 0 else 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    return round(rsi, 2)

def compute_volatility(closes: list[float], window: int = 20) -> float | None:
    """Annualized realized volatility over the last `window` days."""
    if window < 2:
        raise ValueError("Volatility window must be at least two.")
    if len(closes) < window + 1:
        return None

    log_returns = []
    for i in range(len(closes) - window, len(closes)):
        daily_return = math.log(closes[i] / closes[i - 1])
        log_returns.append(daily_return)

    mean = sum(log_returns) / len(log_returns)

    squared_diffs = []
    for r in log_returns:
        squared_diffs.append((r - mean) ** 2)
    variance = sum(squared_diffs) / (len(log_returns) - 1)

    daily_vol = math.sqrt(variance)
    annual_vol = daily_vol * math.sqrt(252)
    return round(annual_vol * 100, 2)

def find_support_resistance(highs: list[float], lows: list[float], window: int = 5) -> tuple[list[float], list[float]]:
    """Find pivot highs and pivot lows using a left/right window comparison."""
    pivot_highs = []
    pivot_lows = []

    for i in range(window, len(highs) - window):

        is_pivot_high = True
        for j in range(1, window + 1):
            if highs[i] < highs[i - j] or highs[i] < highs[i + j]:
                is_pivot_high = False
                break
        if is_pivot_high:
            pivot_highs.append(highs[i])

        is_pivot_low = True
        for j in range(1, window + 1):
            if lows[i] > lows[i - j] or lows[i] > lows[i + j]:
                is_pivot_low = False
                break
        if is_pivot_low:
            pivot_lows.append(lows[i])

    return pivot_highs, pivot_lows

def compute_volume_signal(volumes: list[int]) -> dict:
    """Compare today's volume to the 20-day average."""
    if len(volumes) < 20:
        return {"avg_20": None, "latest": None, "ratio": None, "signal": "unknown"}

    avg_20 = sum(volumes[-20:]) / 20
    latest = volumes[-1]
    ratio = round(latest / avg_20, 2) if avg_20 > 0 else None

    if ratio is None:
        signal = "unknown"
    elif ratio > 1.5:
        signal = "high"
    elif ratio < 0.6:
        signal = "low"
    else:
        signal = "normal"

    return {
        "avg_20": int(avg_20),
        "latest": latest,
        "ratio": ratio,
        "signal": signal,
    }

def compute_signals(ohlcv: dict) -> dict:
    """Take raw OHLCV dict and return all five signal blocks."""
    fields = ("closes", "opens", "highs", "lows", "volumes", "timestamps")
    if not ohlcv.get("closes") or any(len(ohlcv.get(k, [])) != len(ohlcv["closes"]) for k in fields):
        raise ValueError("OHLCV arrays must be nonempty and aligned.")
    for key in ("closes", "opens", "highs", "lows"):
        if any(not math.isfinite(v) or v <= 0 for v in ohlcv[key]):
            raise ValueError("Prices must be finite and positive.")
    if any(not math.isfinite(v) or v < 0 for v in ohlcv["volumes"]):
        raise ValueError("Volumes must be finite and nonnegative.")
    closes = ohlcv["closes"]
    highs = ohlcv["highs"]
    lows = ohlcv["lows"]
    current_price = closes[-1]

    ma20_series = simple_moving_average(closes, 20)
    ma50_series = simple_moving_average(closes, 50)
    ma20 = ma20_series[-1]
    ma50 = ma50_series[-1]

    if ma20 is not None:
        price_above_ma20 = current_price > ma20
    else:
        price_above_ma20 = None

    if ma50 is not None:
        price_above_ma50 = current_price > ma50
    else:
        price_above_ma50 = None

    if ma20 is not None and ma50 is not None:
        ma20_above_ma50 = ma20 > ma50
    else:
        ma20_above_ma50 = None

    if ma20 is None or ma50 is None:
        trend_signal = "unknown"
    elif price_above_ma20 and price_above_ma50 and ma20_above_ma50:
        trend_signal = "bullish"
    elif current_price < ma20 and current_price < ma50:
        trend_signal = "bearish"
    else:
        trend_signal = "neutral"

    rounded_ma20 = []
    for value in ma20_series:
        if value is not None:
            rounded_ma20.append(round(value, 2))
        else:
            rounded_ma20.append(None)

    rounded_ma50 = []
    for value in ma50_series:
        if value is not None:
            rounded_ma50.append(round(value, 2))
        else:
            rounded_ma50.append(None)

    trend = {
        "ma20": round(ma20, 2) if ma20 else None,
        "ma50": round(ma50, 2) if ma50 else None,
        "ma20_series": rounded_ma20,
        "ma50_series": rounded_ma50,
        "price_above_ma20": price_above_ma20,
        "price_above_ma50": price_above_ma50,
        "ma20_above_ma50": ma20_above_ma50,
        "signal": trend_signal,
    }

    rsi = compute_rsi(closes)

    if len(closes) >= 22:
        price_21_days_ago = closes[-22]
        one_month_return = ((current_price - price_21_days_ago) / price_21_days_ago) * 100
        one_month_return = round(one_month_return, 2)
    else:
        one_month_return = None

    if rsi is not None and rsi > 70:
        momentum_signal = "stretched"
    elif rsi is not None and rsi < 30:
        momentum_signal = "weak"
    elif one_month_return is not None and one_month_return > 5 and rsi is not None and rsi > 50:
        momentum_signal = "supportive"
    else:
        momentum_signal = "mixed"

    momentum = {
        "rsi": rsi,
        "one_month_return": one_month_return,
        "signal": momentum_signal,
    }

    vol = compute_volatility(closes)

    if vol is not None:
        if vol < 20:
            vol_signal = "low"
        elif vol < 35:
            vol_signal = "medium"
        else:
            vol_signal = "high"
    else:
        vol_signal = "unknown"

    volatility = {
        "realized_vol_20d": vol,
        "signal": vol_signal,
    }

    pivot_highs, pivot_lows = find_support_resistance(highs, lows)

    supports = []
    for price in pivot_lows:
        if price < current_price:
            supports.append(price)
    supports = sorted(set(supports), reverse=True)

    if len(supports) >= 1:
        nearest_support = round(supports[0], 2)
    else:
        nearest_support = None

    if len(supports) >= 2:
        second_support = round(supports[1], 2)
    else:
        second_support = None

    resistances = []
    for price in pivot_highs:
        if price > current_price:
            resistances.append(price)
    resistances = sorted(set(resistances))

    if len(resistances) >= 1:
        nearest_resistance = round(resistances[0], 2)
    else:
        nearest_resistance = None

    if len(resistances) >= 2:
        second_resistance = round(resistances[1], 2)
    else:
        second_resistance = None

    if nearest_support and nearest_resistance:
        range_size = nearest_resistance - nearest_support
        if range_size > 0:
            position_in_range = (current_price - nearest_support) / range_size
            if position_in_range < 0.25:
                levels_signal = "near_support"
            elif position_in_range > 0.75:
                levels_signal = "near_resistance"
            else:
                levels_signal = "mid_range"
        else:
            levels_signal = "breakout_zone"
    elif nearest_resistance and not nearest_support:
        levels_signal = "near_resistance"
    elif nearest_support and not nearest_resistance:
        levels_signal = "breakout_zone"
    else:
        levels_signal = "unknown"

    levels = {
        "nearest_support": nearest_support,
        "second_support": second_support,
        "nearest_resistance": nearest_resistance,
        "second_resistance": second_resistance,
        "signal": levels_signal,
    }

    volume = compute_volume_signal(ohlcv["volumes"])

    return {
        "current_price": round(current_price, 2),
        "trend": trend,
        "momentum": momentum,
        "volatility": volatility,
        "levels": levels,
        "volume": volume,
    }
