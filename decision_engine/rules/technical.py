from typing import Any


def evaluate_technical_indicators(
    rsi: float | None,
    macd_hist: float | None,
    trend_strength: float | None
) -> tuple[float, list[str], list[str]]:
    """
    Evaluates Technical Indicators (RSI, MACD, MA trend strength).
    Weight: 20%
    """
    reasons = []
    rules = []
    scores = []

    # 1. RSI
    if rsi is not None:
        if rsi <= 30.0:
            scores.append(100.0)
            reasons.append(f"RSI is oversold at {rsi:.2f} (<= 30).")
            rules.append("RSI_OVERSOLD")
        elif rsi >= 70.0:
            scores.append(20.0)
            reasons.append(f"RSI is overbought at {rsi:.2f} (>= 70).")
            rules.append("RSI_OVERBOUGHT")
        else:
            scores.append(50.0)
            rules.append("RSI_NEUTRAL")
    else:
        scores.append(50.0)

    # 2. MACD
    if macd_hist is not None:
        if macd_hist > 0.0:
            scores.append(80.0)
            reasons.append("MACD histogram shows bullish upward momentum (MACD > Signal).")
            rules.append("MACD_BULLISH")
        else:
            scores.append(40.0)
            reasons.append("MACD histogram shows bearish momentum (MACD <= Signal).")
            rules.append("MACD_BEARISH")
    else:
        scores.append(50.0)

    # 3. MA Trend Strength (separation of EMA 20 vs SMA 50)
    if trend_strength is not None:
        if trend_strength > 5.0:
            scores.append(80.0)
            reasons.append(f"Trend strength separation shows strong bullish extension ({trend_strength:.2f}%).")
            rules.append("TREND_STRONG_BULLISH")
        elif trend_strength < -5.0:
            scores.append(40.0)
            reasons.append(f"Trend strength separation shows strong bearish correction ({trend_strength:.2f}%).")
            rules.append("TREND_STRONG_BEARISH")
        else:
            scores.append(50.0)
            rules.append("TREND_NEUTRAL")
    else:
        scores.append(50.0)

    avg_score = sum(scores) / len(scores)
    return avg_score, reasons, rules
