import pandas as pd


def calculate_drawdown(series: pd.Series, window: int = 252) -> pd.Series:
    """
    Calculates percentage drawdown of Close prices relative to rolling peak over a window.
    """
    rolling_max = series.rolling(window=window, min_periods=1).max()
    return (series - rolling_max) / (rolling_max + 1e-10)


def calculate_volatility(series: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculates rolling standard deviation of daily percentage Close returns over a period.
    """
    returns = series.pct_change()
    return returns.rolling(window=period).std()
