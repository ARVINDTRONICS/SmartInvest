import email.utils
import logging
from datetime import date, datetime, UTC
import httpx
from bs4 import BeautifulSoup
import pytz
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from collectors.base import BaseCollector
from collectors.utils import retry_async
from database.models import News

logger = logging.getLogger(__name__)

# News sources mapping: Friendly Name -> RSS Feed details
NEWS_SOURCES = {
    "Reuters": {
        "url": "https://news.google.com/rss/search?q=site:reuters.com+finance&hl=en-US&gl=US&ceid=US:en",
        "country": "US"
    },
    "Bloomberg": {
        "url": "https://news.google.com/rss/search?q=site:bloomberg.com+finance&hl=en-US&gl=US&ceid=US:en",
        "country": "US"
    },
    "CNBC": {
        "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "country": "US"
    },
    "Economic Times": {
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "country": "IN"
    },
    "Moneycontrol": {
        "url": "https://www.moneycontrol.com/rss/latestnews.xml",
        "country": "IN"
    },
    "RBI": {
        "url": "https://rbi.org.in/pressreleases_rss.xml",
        "country": "IN"
    },
    "Federal Reserve": {
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "country": "US"
    },
    "NSE": {
        "url": "https://news.google.com/rss/search?q=site:nseindia.com+corporates&hl=en-IN&gl=IN&ceid=IN:en",
        "country": "IN"
    },
    "BSE": {
        "url": "https://news.google.com/rss/search?q=site:bseindia.com+corporates&hl=en-IN&gl=IN&ceid=IN:en",
        "country": "IN"
    }
}


class NewsCollector(BaseCollector):
    """
    Collector for daily financial news, central bank policies, and exchange announcements.
    Parses RSS feeds and extracts cleaned raw body content from articles.
    """
    def __init__(self) -> None:
        super().__init__(name="news")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }

    def _parse_pub_date(self, date_str: str) -> datetime:
        """
        Parses various RSS date string formats into timezone-aware UTC datetime.
        """
        date_str = date_str.strip()
        try:
            # Parses standard RFC 822 format (e.g. "Thu, 16 Jul 2026 18:00:00 GMT")
            dt = email.utils.parsedate_to_datetime(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except Exception:
            # Fallback for RBI dates without timezone (e.g. "Fri, 24 Jul 2026 19:15:00")
            for fmt in ["%a, %d %b %Y %H:%M:%S", "%a, %d %b %Y"]:
                try:
                    naive_dt = datetime.strptime(date_str, fmt)
                    tz = pytz.timezone("Asia/Kolkata")
                    localized_dt = tz.localize(naive_dt)
                    return localized_dt.astimezone(UTC)
                except ValueError:
                    continue
            self.logger.warning(f"Could not parse news date string: '{date_str}', utilizing UTC fallback.")
            return datetime.now(UTC)

    async def _fetch_raw_content(self, url: str) -> str | None:
        """
        Downloads article page HTML and extracts clean text content from <p> paragraphs.
        """
        async def fetch() -> bytes:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=12.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content

        try:
            html_content = await retry_async(fetch)
            soup = BeautifulSoup(html_content, "lxml")
            
            # Remove boilerplates and visual components
            for elem in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe"]):
                elem.extract()

            # Retrieve text from all standard paragraphs
            paragraphs = [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]
            if paragraphs:
                return "\n\n".join(paragraphs)
            return None
        except Exception as e:
            self.logger.warning(f"Failed to crawl raw content from: {url} -> {e}")
            return None

    async def collect_daily(self, db: AsyncSession) -> None:
        """
        Retrieves today's news from all sources.
        """
        # For daily runs, we scan current RSS items and extract new articles
        await self.collect_historical(db, date.today(), date.today())

    async def collect_historical(self, db: AsyncSession, start_date: date, end_date: date) -> None:
        """
        Parses RSS feeds and collects articles published within the start_date and end_date window.
        """
        for source_name, details in NEWS_SOURCES.items():
            self.logger.info(f"Collecting news for: {source_name}")
            
            async def fetch_rss() -> bytes:
                async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=15.0) as client:
                    response = await client.get(details["url"])
                    response.raise_for_status()
                    return response.content

            try:
                rss_content = await retry_async(fetch_rss)
                soup = BeautifulSoup(rss_content, "xml")
                items = soup.find_all("item")
                
                new_articles_count = 0
                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    date_elem = item.find("pubDate") or item.find("date")
                    desc_elem = item.find("description")

                    if not title_elem or not link_elem or not date_elem:
                        continue

                    headline = title_elem.text.strip()
                    url = link_elem.text.strip()
                    pub_date = self._parse_pub_date(date_elem.text)

                    # Filter by date range (only comparing the date component)
                    article_date = pub_date.date()
                    if article_date < start_date or article_date > end_date:
                        continue

                    # Check if article exists in DB to prevent redundant crawl requests
                    stmt = select(News.id).where(News.url == url)
                    result = await db.execute(stmt)
                    if result.scalar_one_or_none() is not None:
                        continue

                    # Fetch raw text
                    self.logger.debug(f"Crawling raw content for: {url}")
                    raw_content = await self._fetch_raw_content(url)

                    # Map summary to RSS description, or truncate raw content if empty
                    summary = desc_elem.text.strip() if desc_elem else ""
                    if not summary and raw_content:
                        summary = raw_content[:250] + "..." if len(raw_content) > 250 else raw_content

                    # Save to database using upsert logic
                    upsert_stmt = insert(News).values(
                        headline=headline,
                        source=source_name,
                        country=details["country"],
                        published_date=pub_date,
                        url=url,
                        raw_content=raw_content,
                        summary=summary
                    )
                    
                    # On conflict (e.g. duplicate URL), update fields
                    upsert_stmt = upsert_stmt.on_conflict_do_update(
                        index_elements=["url"],
                        set_={
                            "headline": upsert_stmt.excluded.headline,
                            "raw_content": upsert_stmt.excluded.raw_content,
                            "summary": upsert_stmt.excluded.summary,
                        }
                    )
                    await db.execute(upsert_stmt)
                    new_articles_count += 1

                await db.commit()
                self.logger.info(f"Completed {source_name}: Saved {new_articles_count} new articles.")
            except Exception as e:
                self.logger.error(f"Failed news collection for source {source_name}: {e}", exc_info=True)
