import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from crawler.crawler import TechStackCrawler


class TestCrawler(unittest.TestCase):
    """Unit tests for the async web crawler parser and logic."""

    def test_user_agent_rotation(self):
        """Test that headers return randomized user agents."""
        crawler = TechStackCrawler()
        ua1 = crawler._get_headers()["User-Agent"]
        ua2 = crawler._get_headers()["User-Agent"]
        
        # Check that it returns one of our defined user agents
        from crawler.crawler import USER_AGENTS
        self.assertIn(ua1, USER_AGENTS)
        self.assertIn(ua2, USER_AGENTS)

    @patch("aiohttp.ClientSession")
    def test_fetch_page_parsing(self, mock_session_class):
        """Test that fetch_page correctly parses page headers, title, scripts, and meta tags."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run():
            crawler = TechStackCrawler()
            
            # Setup mock aiohttp ClientSession and response
            mock_session = MagicMock()
            crawler.session = mock_session
            
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.url = MagicMock()
            mock_response.url.__str__ = MagicMock(return_value="https://example.com")
            mock_response.headers = {"Server": "Cloudflare", "Content-Type": "text/html"}
            
            # Mock the async text response
            mock_response.text = AsyncMock(return_value="""
            <html>
                <head>
                    <title>Test Page Title</title>
                    <meta name="generator" content="WordPress 6.4">
                    <link href="https://cdn.example.com/style.css" rel="stylesheet">
                </head>
                <body>
                    <h1>Hello World</h1>
                    <script src="https://www.google-analytics.com/analytics.js"></script>
                    <script>console.log("inline script");</script>
                </body>
            </html>
            """)
            
            # Mock get() context manager
            mock_get_ctx = MagicMock()
            mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.get.return_value = mock_get_ctx
            
            # Run fetch_page
            result = await crawler.fetch_page("https://example.com")
            
            # Verify result dictionary
            self.assertIsNotNone(result)
            self.assertEqual(result["status"], 200)
            self.assertEqual(result["page_title"], "Test Page Title")
            self.assertEqual(result["meta_generator"], "WordPress 6.4")
            self.assertEqual(result["url"], "https://example.com")
            
            # Verify headers and scripts extraction
            self.assertEqual(result["headers"]["Server"], "Cloudflare")
            self.assertIn("https://www.google-analytics.com/analytics.js", result["scripts"])
            self.assertIn("console.log(\"inline script\");", result["scripts"])
            self.assertIn("https://cdn.example.com/style.css", result["scripts"])
            
        loop.run_until_complete(run())
        loop.close()


if __name__ == "__main__":
    unittest.main()
