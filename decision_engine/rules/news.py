
def evaluate_news_sentiment(headlines: list[str]) -> tuple[float, list[str], list[str]]:
    """
    Evaluates news headlines sentiment.
    Weight: 15%
    """
    reasons = []
    rules = []

    if not headlines:
        reasons.append("No news articles collected today; neutral sentiment assumed.")
        rules.append("NEWS_NEUTRAL")
        return 50.0, reasons, rules

    bullish_words = ["bullish", "rally", "growth", "recovery", "surge", "upgrade", "positive", "expansion", "profit"]
    bearish_words = ["bearish", "crash", "fall", "drop", "inflation", "recession", "war", "crisis", "conflict", "slowdown"]

    bull_count = 0
    bear_count = 0

    for headline in headlines:
        headline_lower = headline.lower()
        for word in bullish_words:
            if word in headline_lower:
                bull_count += 1
        for word in bearish_words:
            if word in headline_lower:
                bear_count += 1

    total = bull_count + bear_count
    if total == 0:
        reasons.append("News articles collected showed neutral sentiment metrics.")
        rules.append("NEWS_NEUTRAL")
        return 50.0, reasons, rules

    bull_ratio = bull_count / total
    score = bull_ratio * 100.0

    if score >= 65.0:
        reasons.append(f"News sentiment is highly positive ({bull_ratio * 100:.1f}% bullish keywords).")
        rules.append("NEWS_BULLISH")
    elif score <= 35.0:
        reasons.append(f"News sentiment is bearish ({ (1 - bull_ratio) * 100:.1f}% bearish keywords).")
        rules.append("NEWS_BEARISH")
    else:
        reasons.append(f"News sentiment is neutral ({bull_ratio * 100:.1f}% bullish keywords).")
        rules.append("NEWS_NEUTRAL")

    return score, reasons, rules
