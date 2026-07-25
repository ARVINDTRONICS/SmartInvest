from typing import Any

from decision_engine.rules.market import evaluate_market_trend
from decision_engine.rules.technical import evaluate_technical_indicators
from decision_engine.rules.macro import evaluate_macro_environment
from decision_engine.rules.news import evaluate_news_sentiment
from decision_engine.rules.volatility import evaluate_volatility_vix
from decision_engine.rules.liquidity import evaluate_liquidity_score


def calculate_decision_score(
    close: float,
    sma_50: float | None,
    sma_200: float | None,
    rsi: float | None,
    macd_hist: float | None,
    trend_strength: float | None,
    headlines: list[str],
    vix_value: float | None,
    liq_score: float | None,
    remaining_days: int
) -> tuple[str, int, list[str], list[str]]:
    """
    Computes decision and confidence score based on deterministic rules.
    If remaining_days == 1, enforces INVEST decision immediately.
    """
    # 1. Final window day check
    if remaining_days <= 1:
        return (
            "INVEST",
            100,
            ["Forced execution: Today is the final day of the configured investment window. Investment execution is mandatory."],
            ["FORCED_EXECUTION"]
        )

    # 2. Evaluate all category rules
    m_score, m_reasons, m_rules = evaluate_market_trend(close, sma_50, sma_200)
    t_score, t_reasons, t_rules = evaluate_technical_indicators(rsi, macd_hist, trend_strength)
    mac_score, mac_reasons, mac_rules = evaluate_macro_environment()
    n_score, n_reasons, n_rules = evaluate_news_sentiment(headlines)
    v_score, v_reasons, v_rules = evaluate_volatility_vix(vix_value)
    l_score, l_reasons, l_rules = evaluate_liquidity_score(liq_score)

    # 3. Calculate weighted confidence score
    weighted_score = (
        (m_score * 0.25) +
        (mac_score * 0.20) +
        (t_score * 0.20) +
        (n_score * 0.15) +
        (v_score * 0.10) +
        (l_score * 0.10)
    )

    confidence = int(round(weighted_score))
    
    # If confidence score is 60 or above, recommend INVEST, otherwise WAIT
    decision = "INVEST" if confidence >= 60 else "WAIT"

    # Blend details
    reasons = m_reasons + t_reasons + mac_reasons + n_reasons + v_reasons + l_reasons
    triggered_rules = m_rules + t_rules + mac_rules + n_rules + v_rules + l_rules

    return decision, confidence, reasons, triggered_rules
