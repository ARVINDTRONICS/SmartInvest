import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from indicators.trend.ma import calculate_sma, calculate_ema, calculate_trend_strength
from indicators.volatility.indicators import calculate_drawdown, calculate_volatility
from indicators.momentum.indicators import calculate_rsi, calculate_macd, calculate_momentum
from indicators.valuation.indicators import calculate_liquidity_score
from indicators.engine import IndicatorsEngine


def test_ma_calculations() -> None:
    """
    Test SMA, EMA, and Trend Strength formulas.
    """
    series = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
    
    sma = calculate_sma(series, 3)
    assert pd.isna(sma.iloc[0])
    assert sma.iloc[2] == 11.0  # (10+11+12)/3
    assert sma.iloc[4] == 13.0  # (12+13+14)/3

    ema = calculate_ema(series, 3)
    assert ema.iloc[0] == 10.0
    # Multiplier: 2 / (3 + 1) = 0.5
    # ema[1] = 11 * 0.5 + 10 * 0.5 = 10.5
    assert ema.iloc[1] == 10.5

    trend_str = calculate_trend_strength(pd.Series([110.0]), pd.Series([100.0]))
    assert trend_str.iloc[0] == pytest.approx(10.0)


def test_volatility_drawdown() -> None:
    """
    Test drawdown calculation and volatility rolling return logic.
    """
    series = pd.Series([100.0, 105.0, 90.0, 95.0])
    dd = calculate_drawdown(series, window=4)
    # Peak Close value is 105.0 at idx 1
    # drawdown at idx 2 = (90.0 - 105.0) / 105.0 = -0.142857
    assert round(dd.iloc[2], 4) == -0.1429

    vol = calculate_volatility(pd.Series([10.0, 10.1, 10.0, 10.2]), period=3)
    assert vol.notna().any()


def test_momentum_indicators() -> None:
    """
    Test RSI, MACD, and Momentum calculations.
    """
    series = pd.Series(range(1, 20), dtype=float)
    
    rsi = calculate_rsi(series, period=5)
    assert rsi.notna().any()

    macd, signal, hist = calculate_macd(series)
    assert macd.notna().any()
    assert signal.notna().any()
    assert hist.notna().any()

    mom = calculate_momentum(series, period=5)
    assert mom.notna().any()


@pytest.mark.asyncio
async def test_indicators_engine() -> None:
    """
    Test that the IndicatorsEngine properly fetches historical market data, 
    calculates features, fetches global market breadth/fear indexes, and stores records.
    """
    db_mock = AsyncMock()

    class MockMarketRecord:
        def __init__(self, dt: date, val: float, vol: int):
            self.date = dt
            self.open = val
            self.high = val
            self.low = val
            self.close = val
            self.volume = vol

    # Create 60 historical day records to allow SMA 50 calculations
    start_dt = date(2026, 1, 1)
    mock_records = [
        MockMarketRecord(start_dt + timedelta(days=i), 100.0 + i, 1000) for i in range(60)
    ]

    # 1. Target asset history query result
    res_symbol = MagicMock()
    res_symbol.scalars.return_value.all.return_value = mock_records

    # 2. Sector index query result
    res_sector = MagicMock()
    res_sector.all.return_value = [(start_dt + timedelta(days=i), 100.0) for i in range(60)]

    # 3. Fear index query result (VIX)
    res_vix = MagicMock()
    res_vix.all.return_value = [(start_dt + timedelta(days=i), 15.0) for i in range(60)]

    # Custom execute mocker to handle both selects and inserts
    async def mock_execute(statement, *args, **kwargs) -> MagicMock:
        stmt_str = str(statement).lower()
        if "select" in stmt_str:
            if any(sec.lower() in stmt_str for sec in ["nifty_it", "nifty_pharma", "nifty_fmcg", "nifty_metal", "nifty_auto", "nifty_realty", "nifty_fin"]):
                return res_sector
            elif "indiavix" in stmt_str or "usvix" in stmt_str:
                return res_vix
            else:
                return res_symbol
        # Return empty mock for upsert statements
        return MagicMock()

    db_mock.execute.side_effect = mock_execute

    engine = IndicatorsEngine()
    await engine.calculate_for_symbol(db_mock, "NIFTY50")

    # Assert queries were run and updates committed
    assert db_mock.execute.call_count > 1
    assert db_mock.commit.call_count >= 1
