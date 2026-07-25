from collectors.yfinance_base import YFinanceBaseCollector

# Symbol mapping: DB representation -> Yahoo Finance ticker
US_SYMBOLS = {
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
    "SP500": "^GSPC",
    "USVIX": "^VIX",
}


class USIndexCollector(YFinanceBaseCollector):
    """
    Collector for major US stock market indices.
    """
    def __init__(self) -> None:
        super().__init__(name="us_index", symbols=US_SYMBOLS)
