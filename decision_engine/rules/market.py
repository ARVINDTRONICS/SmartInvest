from typing import Any


def evaluate_market_trend(
    close: float, sma_50: float | None, sma_200: float | None
) -> tuple[float, list[str], list[str]]:
    """
    Evaluates market trend status.
    Weight: 25%
    """
    reasons = []
    rules = []

    if sma_50 is None or sma_200 is None:
        reasons.append("Insufficient moving average data to establish trend.")
        rules.append("TREND_UNKNOWN")
        return 50.0, reasons, rules

    # Bull Market (above SMA 200)
    if close >= sma_200:
        if close < sma_50:
            # Pullback correction in bull market -> ideal buy opportunity!
            reasons.append("Asset experiencing pullback correction within long-term bull market (Close < SMA 50, but Close >= SMA 200).")
            rules.append("BULL_CORRECTION")
            return 90.0, reasons, rules
        else:
            # Standard bull uptrend
            reasons.append("Asset in established long-term uptrend above SMA 50 and SMA 200.")
            rules.append("BULL_UPTREND")
            return 60.0, reasons, rules
    # Bear Market (below SMA 200)
    else:
        if close >= sma_50:
            # Bear market rally
            reasons.append("Bear market rally detected: price recovered above SMA 50 but remains below SMA 200.")
            rules.append("BEAR_RALLY")
            return 40.0, reasons, rules
        else:
            # Severe bear downtrend
            reasons.append("Asset in severe downtrend below SMA 50 and SMA 200.")
            rules.append("BEAR_DOWNTREND")
            return 30.0, reasons, rules
