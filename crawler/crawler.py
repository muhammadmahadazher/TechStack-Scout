"""
Async web crawler for TechStack Scout.
Built with aiohttp for high-performance concurrent crawling.
"""

import asyncio
import aiohttp
import ssl
import certifi
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional, Set
import time
import random

from .signatures import detect_technologies
from .db import (
    get_pending_domains,
    update_domain_crawl_result,
    add_tech_detections_batch,
    get_pool,
    close_pool
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crawler")

# SSL context that actually works
ssl_context = ssl.create_default_context(cafile=certifi.where())

# User agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class TechStackCrawler:
    """High-performance async web crawler for technology detection."""

    def __init__(
        self,
        max_concurrent: int = 10,
        request_timeout: int = 15,
        max_retries: int = 2,
        delay_between_requests: float = 0.5,
        respect_robots: bool = True
    ):
        self.max_concurrent = max_concurrent
        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.delay_between_requests = delay_between_requests
        self.respect_robots = respect_robots
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "technologies_found": 0,
            "start_time": None,
        }

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            enable_cleanup_closed=True,
            force_close=True,
        )

        timeout = aiohttp.ClientTimeout(total=self.request_timeout)

        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        """Get randomized request headers."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
        }

    async def fetch_page(self, url: str, retries: int = 0) -> Optional[Dict]:
        """Fetch a single page and extract data."""
        async with self.semaphore:
            try:
                async with asyncio.timeout(self.request_timeout):
                    async with self.session.get(
                        url,
                        headers=self._get_headers(),
                        ssl=ssl_context,
                        allow_redirects=True,
                        max_redirects=5,
                    ) as response:

                        # Get headers
                        headers = dict(response.headers)

                        # Get content
                        content = await response.text()

                        # Parse HTML
                        soup = BeautifulSoup(content, "html.parser")

                        # Extract page title
                        title_tag = soup.find("title")
                        page_title = title_tag.get_text(strip=True) if title_tag else None

                        # Extract meta generator
                        meta_generator = None
                        meta = soup.find("meta", attrs={"name": "generator"})
                        if meta:
                            meta_generator = meta.get("content")

                        # Extract all script sources
                        scripts = []
                        for script in soup.find_all("script", src=True):
                            scripts.append(script["src"])

                        # Extract inline scripts for detection
                        for script in soup.find_all("script", string=True):
                            scripts.append(script.string[:500] if script.string else "")

                        # Extract link tags (stylesheets, etc)
                        for link in soup.find_all("link", href=True):
                            scripts.append(link["href"])

                        return {
                            "url": str(response.url),
                            "status": response.status,
                            "headers": headers,
                            "html_content": content,
                            "page_title": page_title,
                            "meta_generator": meta_generator,
                            "scripts": scripts,
                            "page_size": len(content.encode("utf-8")),
                        }

            except (asyncio.TimeoutError, TimeoutError):
                if retries < self.max_retries:
                    await asyncio.sleep(1 * (retries + 1))
                    return await self.fetch_page(url, retries + 1)
                logger.warning(f"Timeout after {retries + 1} retries: {url}")
                return None

            except aiohttp.ClientError as e:
                if retries < self.max_retries:
                    await asyncio.sleep(1 * (retries + 1))
                    return await self.fetch_page(url, retries + 1)
                logger.warning(f"Client error after {retries + 1} retries: {url} - {e}")
                return None

            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                return None

            finally:
                # Polite delay
                if self.delay_between_requests > 0:
                    await asyncio.sleep(self.delay_between_requests)

    async def crawl_domain(self, domain_data: Dict) -> Dict:
        """Crawl a single domain and detect technologies."""
        domain_id = domain_data["id"]
        domain = domain_data["domain"]

        # Try HTTPS first, then HTTP
        urls = [f"https://{domain}", f"http://{domain}"]

        result = {
            "domain_id": domain_id,
            "domain": domain,
            "success": False,
            "technologies": [],
            "error": None,
        }

        for url in urls:
            page_data = await self.fetch_page(url)

            if page_data and page_data["status"] < 400:
                # Detect technologies
                detections = detect_technologies(
                    page_data["headers"],
                    page_data["html_content"],
                    page_data["scripts"]
                )

                # Update domain in DB
                server_header = page_data["headers"].get("Server", "")
                await update_domain_crawl_result(
                    domain_id=domain_id,
                    status="crawled",
                    page_title=page_data["page_title"],
                    http_status=page_data["status"],
                    page_size=page_data["page_size"],
                    server_header=server_header[:255] if server_header else None,
                    meta_generator=page_data["meta_generator"][:255] if page_data["meta_generator"] else None,
                )

                # Add detections
                if detections:
                    await add_tech_detections_batch(domain_id, detections)

                result["success"] = True
                result["technologies"] = detections
                result["page_title"] = page_data["page_title"]
                result["http_status"] = page_data["status"]

                self.stats["success"] += 1
                self.stats["technologies_found"] += len(detections)

                logger.info(f"[OK] {domain} - {len(detections)} technologies detected")
                break

            elif page_data and page_data["status"] >= 400:
                # Server responded but with error
                await update_domain_crawl_result(
                    domain_id=domain_id,
                    status="failed",
                    http_status=page_data["status"],
                    error_message=f"HTTP {page_data['status']}"
                )
                result["error"] = f"HTTP {page_data['status']}"
                self.stats["failed"] += 1
                break

        else:
            # All URLs failed
            await update_domain_crawl_result(
                domain_id=domain_id,
                status="failed",
                error_message=result.get("error", "Connection failed")
            )
            result["error"] = result.get("error", "Connection failed")
            self.stats["failed"] += 1
            logger.warning(f"[FAIL] {domain} - Failed to crawl")

        self.stats["total"] += 1
        return result

    async def crawl_batch(self, domains: List[Dict]) -> List[Dict]:
        """Crawl a batch of domains concurrently."""
        tasks = [self.crawl_domain(d) for d in domains]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Crawl task failed: {r}")
            else:
                valid_results.append(r)

        return valid_results

    async def run(self, batch_size: int = 100, max_batches: Optional[int] = None):
        """Main crawler loop."""
        self.stats["start_time"] = time.time()
        batch_count = 0

        logger.info(f"[START] Crawler started - batch_size={batch_size}, max_concurrent={self.max_concurrent}")

        while True:
            # Get pending domains
            domains = await get_pending_domains(limit=batch_size)

            if not domains:
                logger.info("No more pending domains. Crawler finished.")
                break

            logger.info(f"📦 Batch {batch_count + 1}: {len(domains)} domains")

            # Crawl batch
            results = await self.crawl_batch(domains)

            batch_count += 1

            # Log progress
            elapsed = time.time() - self.stats["start_time"]
            rate = self.stats["total"] / elapsed if elapsed > 0 else 0
            logger.info(
                f"[STATS] Progress: {self.stats['total']} crawled | "
                f"{self.stats['success']} success | {self.stats['failed']} failed | "
                f"{self.stats['technologies_found']} techs found | "
                f"{rate:.1f} domains/sec"
            )

            if max_batches and batch_count >= max_batches:
                logger.info(f"Reached max batches ({max_batches}). Stopping.")
                break

            # Brief pause between batches
            await asyncio.sleep(1)

        # Final stats
        elapsed = time.time() - self.stats["start_time"]
        logger.info(
            f"[FINISHED] Crawler finished in {elapsed:.1f}s | "
            f"Total: {self.stats['total']} | "
            f"Success: {self.stats['success']} | "
            f"Failed: {self.stats['failed']} | "
            f"Technologies: {self.stats['technologies_found']}"
        )


async def run_crawler(batch_size: int = 50, max_concurrent: int = 10, max_batches: Optional[int] = None):
    """Entry point to run the crawler."""
    await get_pool()

    async with TechStackCrawler(max_concurrent=max_concurrent) as crawler:
        await crawler.run(batch_size=batch_size, max_batches=max_batches)

    await close_pool()


if __name__ == "__main__":
    asyncio.run(run_crawler())
