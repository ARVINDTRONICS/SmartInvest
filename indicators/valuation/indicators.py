import pandas as pd


def calculate_liquidity_score(volume_series: pd.Series, period: int = 20) -> pd.Series:
    """
    Calculates Liquidity Score as the current volume relative to rolling average volume.
    """
    avg_volume = volume_series.rolling(window=period).mean()
    return volume_series / (avg_volume + 1e-10)
