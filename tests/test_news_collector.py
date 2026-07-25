import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock
from collectors.news.news_collector import NewsCollector


@pytest.mark.asyncio
async def test_news_collector_success() -> None:
    """
    Verifies that NewsCollector fetches the RSS feed, filters it by date range,
    crawls the article pages, extracts paragraph content, and stores the article in the database.
    """
    db_mock = AsyncMock()
    collector = NewsCollector()

    # Mock RSS feed XML containing 1 news item matching the query date range
    mock_rss_xml = """<?xml version="1.0" encoding="UTF-8" ?>
    <rss version="2.0">
    <channel>
        <title>Test Financial Feed</title>
        <link>http://test.com</link>
        <item>
            <title>Agencies issue statement on sensible banking</title>
            <link>https://www.federalreserve.gov/news/sensible.htm</link>
            <pubDate>Thu, 16 Jul 2026 18:00:00 GMT</pubDate>
            <description>Federal Reserve and others released a joint statement.</description>
        </item>
    </channel>
    </rss>
    """

    # Mock HTML structure of the news article page
    mock_article_html = """
    <html>
        <head><style>body { color: black; }</style></head>
        <body>
            <header><nav>Boilerplate Nav Menu</nav></header>
            <main>
                <h1>Agencies issue statement</h1>
                <p>The Federal Reserve today released a joint statement with banking regulators.</p>
                <p>This statement details guidelines for examinations.</p>
            </main>
            <footer>Footer notes</footer>
            <script>console.log('test')</script>
        </body>
    </html>
    """

    # Mock URL check query (returns None indicating article does not exist in DB)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db_mock.execute.return_value = result_mock

    # Async mock for HTTP calls: returns XML for feeds and HTML for article pages
    async def mock_get(url, *args, **kwargs) -> MagicMock:
        url_str = str(url)
        if "rss" in url_str or "xml" in url_str:
            return MagicMock(status_code=200, content=mock_rss_xml.encode("utf-8"))
        else:
            return MagicMock(status_code=200, content=mock_article_html.encode("utf-8"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get):
        # Trigger historical collection for July 16, 2026
        await collector.collect_historical(db_mock, date(2026, 7, 16), date(2026, 7, 16))

        # Check if database queries were executed and transaction committed
        # Since we have 9 sources, we expect 9 check queries and 9 insert queries = 18 calls
        assert db_mock.execute.call_count == 18
        assert db_mock.commit.call_count == 9

        # Gather all parameters from the execute calls
        execute_calls = db_mock.execute.call_args_list
        inserted_articles = []
        for call in execute_calls:
            called_statement = call[0][0]
            # Verify if it is an insert statement (not a select statement check)
            if hasattr(called_statement, "compile"):
                params = called_statement.compile().params
                if "headline" in params:
                    inserted_articles.append(params)

        assert len(inserted_articles) == 9
        
        # Spot check Federal Reserve insertion values
        fed_article = next(a for a in inserted_articles if a["source"] == "Federal Reserve")
        assert fed_article["headline"] == "Agencies issue statement on sensible banking"
        assert fed_article["country"] == "US"
        assert fed_article["url"] == "https://www.federalreserve.gov/news/sensible.htm"
        assert fed_article["summary"] == "Federal Reserve and others released a joint statement."
        
        # Verify clean content extraction: tags like <script> and <nav> were stripped
        # and only paragraph <p> texts were joined with double newlines
        assert "Boilerplate Nav Menu" not in fed_article["raw_content"]
        assert "console.log" not in fed_article["raw_content"]
        assert fed_article["raw_content"] == (
            "The Federal Reserve today released a joint statement with banking regulators.\n\n"
            "This statement details guidelines for examinations."
        )
