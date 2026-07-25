import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from database.models import Recommendation
from decision_engine.rules.market import evaluate_market_trend
from decision_engine.rules.technical import evaluate_technical_indicators
from decision_engine.rules.volatility import evaluate_volatility_vix
from decision_engine.rules.liquidity import evaluate_liquidity_score
from decision_engine.rules.news import evaluate_news_sentiment
from decision_engine.scoring import calculate_decision_score


def test_rule_evaluators() -> None:
    """
    Test component rule modules evaluate parameters correctly.
    """
    # 1. Market Trend
    score, reasons, rules = evaluate_market_trend(100.0, 105.0, 95.0)
    assert score == 90.0
    assert "BULL_CORRECTION" in rules

    score, reasons, rules = evaluate_market_trend(100.0, 95.0, 90.0)
    assert score == 60.0
    assert "BULL_UPTREND" in rules

    score, reasons, rules = evaluate_market_trend(80.0, 85.0, 90.0)
    assert score == 30.0
    assert "BEAR_DOWNTREND" in rules

    # 2. Technicals
    score, reasons, rules = evaluate_technical_indicators(rsi=25.0, macd_hist=1.0, trend_strength=6.0)
    # RSI (100) + MACD (80) + Trend (80) = 260 / 3 = 86.666
    assert round(score, 2) == 86.67
    assert "RSI_OVERSOLD" in rules
    assert "MACD_BULLISH" in rules
    assert "TREND_STRONG_BULLISH" in rules

    # 3. Volatility (VIX)
    score, reasons, rules = evaluate_volatility_vix(vix_value=25.0)
    assert score == 90.0
    assert "VIX_HIGH" in rules

    # 4. Liquidity Score
    score, reasons, rules = evaluate_liquidity_score(liq_score=1.3)
    assert score == 80.0
    assert "LIQUIDITY_HIGH" in rules

    # 5. News Sentiment
    score, reasons, rules = evaluate_news_sentiment(headlines=["Markets surge on positive earnings growth", "Profits rally"])
    assert score == 100.0
    assert "NEWS_BULLISH" in rules


def test_scoring_matrix_and_terminal_condition() -> None:
    """
    Test final weighted scoring and terminal final-day forced execution condition.
    """
    # Standard decision evaluation
    decision, confidence, reasons, triggered_rules = calculate_decision_score(
        close=100.0,
        sma_50=105.0,
        sma_200=95.0,
        rsi=25.0,
        macd_hist=1.0,
        trend_strength=6.0,
        headlines=["Bullish growth surge"],
        vix_value=25.0,
        liq_score=1.3,
        remaining_days=5
    )
    
    # Check that high scores result in INVEST
    assert decision == "INVEST"
    assert confidence >= 60

    # Enforce Terminal Condition
    forced_decision, forced_conf, forced_reasons, forced_rules = calculate_decision_score(
        close=100.0,
        sma_50=105.0,
        sma_200=95.0,
        rsi=90.0,  # Overbought
        macd_hist=-1.0,  # Bearish
        trend_strength=-10.0,  # Bearish
        headlines=["Bearish crash crisis"],
        vix_value=5.0,  # Low fear
        liq_score=0.2,  # Low liquidity
        remaining_days=1  # FINAL DAY
    )

    assert forced_decision == "INVEST"
    assert forced_conf == 100
    assert "FORCED_EXECUTION" in forced_rules


@pytest.mark.asyncio
async def test_decision_endpoints() -> None:
    """
    Test FastAPI GET /decision and GET /recommendation/latest endpoints.
    """
    client = TestClient(app)
    db_mock = AsyncMock()

    # Predefined response mock from DecisionEngine.evaluate
    mock_eval = {
        "symbol": "NIFTY50",
        "date": "2026-07-25",
        "decision": "WAIT",
        "confidence": 42,
        "reasons": ["Test wait reasons"],
        "triggered_rules": ["TEST_WAIT_RULE"],
        "remaining_window_days": 4
    }

    # Override get_db dependency
    app.dependency_overrides[get_db] = lambda: db_mock

    # Test GET /decision endpoint by mocking the execution evaluator
    with patch("decision_engine.execution.DecisionEngine.evaluate", new_callable=AsyncMock) as patch_eval:
        patch_eval.return_value = mock_eval

        response = client.get("/decision?symbol=NIFTY50&remaining_days=4")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "NIFTY50"
        assert data["decision"] == "WAIT"
        assert data["confidence"] == 42
        assert "TEST_WAIT_RULE" in data["triggered_rules"]

    # Test GET /recommendation/latest
    mock_recommendation = Recommendation(
        symbol="NIFTY50",
        date=date(2026, 7, 25),
        decision="INVEST",
        confidence=85,
        reasons=["Test reasons"],
        triggered_rules=["TEST_RULES"],
        remaining_window_days=3
    )

    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = mock_recommendation
    db_mock.execute.return_value = res_mock

    response = client.get("/recommendation/latest?symbol=NIFTY50")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "NIFTY50"
    assert data["decision"] == "INVEST"
    assert data["confidence"] == 85

    # Clean up overrides
    app.dependency_overrides.clear()
