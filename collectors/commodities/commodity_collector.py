from collectors.yfinance_base import YFinanceBaseCollector

# Symbol mapping: DB representation -> Yahoo Finance ticker
COMMODITY_SYMBOLS = {
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
}


class CommodityCollector(YFinanceBaseCollector):
    """
    Collector for major commodities (Crude Oil, Gold, Silver).
    """
    def __init__(self) -> None:
        super().__init__(name="commodity", symbols=COMMODITY_SYMBOLS)
