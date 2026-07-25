from collectors.yfinance_base import YFinanceBaseCollector

# Symbol mapping: DB representation -> Yahoo Finance ticker
FOREX_SYMBOLS = {
    "USDINR": "USDINR=X",
}


class ForexCollector(YFinanceBaseCollector):
    """
    Collector for currency pairs (USD/INR).
    """
    def __init__(self) -> None:
        super().__init__(name="forex", symbols=FOREX_SYMBOLS)
