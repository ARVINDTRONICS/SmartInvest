import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from ai.graph.workflow import app


@pytest.mark.asyncio
async def test_ai_graph_compilation_and_execution() -> None:
    """
    Verifies that the compiled LangGraph StateGraph executes all nodes
    successfully and formats the final Telegram output correctly.
    """
    # Predefine initial input state
    initial_state = {
        "symbol": "NIFTY50",
        "date": date(2026, 7, 25),
        "remaining_days": 5,
        "recommendation": {
            "decision": "INVEST",
            "confidence": 85,
            "remaining_window_days": 5,
            "triggered_rules": ["BULL_CORRECTION", "RSI_OVERSOLD"]
        }
    }

    # Mock DB query results:
    # 1. Market close price -> return 24350.0
    res_m = MagicMock()
    res_m.scalar_one_or_none.return_value = 24350.0

    # 2. Technical indicators -> return a mock record
    class MockTechRecord:
        sma_50 = 24100.0
        sma_200 = 23500.0
        rsi = 28.0
        fear_index = 18.0

    res_t = MagicMock()
    res_t.scalar_one_or_none.return_value = MockTechRecord()

    # 3. News articles -> return mock list
    class MockArticle:
        source = "Reuters"
        headline = "India inflation falls to low levels"

    res_n = MagicMock()
    res_n.all.return_value = [MockArticle()]

    # Setup the execution mock side effects
    db_mock = AsyncMock()
    db_mock.execute.side_effect = [res_m, res_t, res_n]

    # Patch the session factory to return our mock DB session context manager
    class AsyncContextManagerMock:
        async def __aenter__(self) -> AsyncMock:
            return db_mock
        async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
            pass

    # Patch the async_session_factory inside ai.graph.nodes where it is used
    with patch("ai.graph.nodes.async_session_factory", return_value=AsyncContextManagerMock()):
        final_state = await app.ainvoke(initial_state)

        # Assert all state parameters were generated correctly by the nodes
        assert "market_text" in final_state
        assert "Asset pricing close: 24350.00" in final_state["market_text"]
        assert "RSI: 28.00" in final_state["market_text"]
        
        assert "news_text" in final_state
        assert "[Reuters] India inflation falls" in final_state["news_text"]

        assert "summary_text" in final_state
        assert "ai_explanation" in final_state
        assert "telegram_text" in final_state

        # Check Telegram text contains the expected formatting
        telegram_output = final_state["telegram_text"]
        assert "*Today's Smart SIP Status: NIFTY50*" in telegram_output
        assert "*Decision*:\n`INVEST`" in telegram_output
        assert "`BULL_CORRECTION, RSI_OVERSOLD`" in telegram_output
