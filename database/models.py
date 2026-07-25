from datetime import date, datetime
from sqlalchemy import Date, DateTime, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class MarketData(Base):
    """
    Stores historical and daily pricing data for indices, sector indices, 
    commodities, and currencies.
    """
    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    close: Mapped[float] = mapped_column(Numeric(precision=18, scale=4), nullable=False)
    volume: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_symbol_date"),
    )


class FIIDIIFlow(Base):
    """
    Stores daily Net flow and Buy/Sell activity of Foreign Institutional Investors (FII)
    and Domestic Institutional Investors (DII) in Crores (INR).
    """
    __tablename__ = "fii_dii_flows"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    
    fii_buy: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    fii_sell: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    fii_net: Mapped[float] = mapped_column(Numeric(precision=18, scale=2), nullable=False)
    
    dii_buy: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    dii_sell: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    dii_net: Mapped[float] = mapped_column(Numeric(precision=18, scale=2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class News(Base):
    """
    Stores financial news articles, announcements, and central bank releases.
    """
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    published_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TechnicalIndicator(Base):
    """
    Stores daily calculated technical indicators and features for assets.
    """
    __tablename__ = "technical_indicators"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    rsi: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    macd: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    sma_50: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    sma_200: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    ema_20: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    drawdown: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    momentum: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    volatility: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    market_breadth: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    trend_strength: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    fear_index: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    liquidity_score: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_indicator_symbol_date"),
    )


class Recommendation(Base):
    """
    Stores calculated daily investment decisions and scores.
    """
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[int] = mapped_column(nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    triggered_rules: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    remaining_window_days: Mapped[int] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_rec_symbol_date"),
    )



