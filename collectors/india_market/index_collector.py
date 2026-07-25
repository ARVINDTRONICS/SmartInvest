from collectors.yfinance_base import YFinanceBaseCollector

# Symbol mapping: DB representation -> Yahoo Finance ticker
INDIA_SYMBOLS = {
    "NIFTY50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK",
    "INDIAVIX": "^INDIAVIX",
    "NIFTY_IT": "^CNXIT",
    "NIFTY_PHARMA": "^CNXPHARMA",
    "NIFTY_FMCG": "^CNXFMCG",
    "NIFTY_METAL": "^CNXMETAL",
    "NIFTY_AUTO": "^CNXAUTO",
    "NIFTY_REALTY": "^CNXREALTY",
    "NIFTY_FIN": "^CNXFIN",
}


class IndiaIndexCollector(YFinanceBaseCollector):
    """
    Collector for major Indian indices and sector indices.
    """
    def __init__(self) -> None:
        super().__init__(name="india_index", symbols=INDIA_SYMBOLS)
