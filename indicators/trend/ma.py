import pandas as pd


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates Simple Moving Average (SMA) of a series for a given period.
    """
    return series.rolling(window=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates Exponential Moving Average (EMA) of a series for a given period.
    """
    return series.ewm(span=period, adjust=False).mean()


def calculate_trend_strength(ema_20: pd.Series, sma_50: pd.Series) -> pd.Series:
    """
    Measures trend strength as percentage separation between EMA 20 and SMA 50.
    """
    return (ema_20 - sma_50) / (sma_50 + 1e-10) * 100
