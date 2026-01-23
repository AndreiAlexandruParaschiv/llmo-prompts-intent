"""Website crawler service using Playwright."""

import os
import json
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CrawlerService:
    """Service for crawling websites and extracting content."""
    
    def __init__(self):
        self.snapshots_dir = settings.SNAPSHOTS_DIR
        self.timeout = settings.CRAWLER_TIMEOUT
        self.rate_limit = settings.CRAWLER_RATE_LIMIT
        os.makedirs(self.snapshots_dir, exist_ok=True)
    
    async def crawl_page(
        self,
        url: str,
        render_js: bool = True,
    ) -> Dict[str, Any]:
        """
        Crawl a single page and extract content.
        
        Args:
            url: URL to crawl
            render_js: Whether to render JavaScript
            
        Returns:
            Dictionary with page data
        """
        from playwright.async_api import async_playwright
        
        result = {
            "url": url,
            "canonical_url": None,
            "status_code": None,
            "content_type": None,
            "title": None,
            "meta_description": None,
            "content": None,
            "word_count": 0,
            "html_snapshot_path": None,
            "structured_data": [],
            "hreflang_tags": [],
            "crawled_at": datetime.utcnow(),
            "error": None,
        }
        
        try:
            async with async_playwright() as p:
                # Launch with stealth-like settings to avoid bot detection
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-http2',  # Avoid HTTP/2 protocol errors
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu',
                        '--window-size=1920,1080',
                    ]
                )
                # Use realistic browser context to avoid detection
                # Updated to latest Chrome user agent (Jan 2026)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York',
                    java_script_enabled=True,
                    bypass_csp=True,
                    ignore_https_errors=True,
                )
                page = await context.new_page()
                
                # Add extra headers to look more like a real browser
                await page.set_extra_http_headers({
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Cache-Control': 'max-age=0',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"macOS"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                })
                
                # Navigate to page with retry on failure
                response = await page.goto(
                    url, 
                    wait_until="networkidle" if render_js else "domcontentloaded",
                    timeout=self.timeout
                )
                
                if response:
                    result["status_code"] = str(response.status)
                    result["content_type"] = response.headers.get("content-type", "")
                
                # Get HTML content
                html_content = await page.content()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, "lxml")
                
                # Extract title
                title_tag = soup.find("title")
                result["title"] = title_tag.get_text().strip() if title_tag else None
                
                # Extract meta description
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    result["meta_description"] = meta_desc.get("content", "").strip()
                
                # Extract canonical URL
                canonical = soup.find("link", attrs={"rel": "canonical"})
                if canonical:
                    result["canonical_url"] = canonical.get("href")
                
                # Extract hreflang tags
                hreflang_tags = soup.find_all("link", attrs={"rel": "alternate", "hreflang": True})
                result["hreflang_tags"] = [
                    {"lang": tag.get("hreflang"), "url": tag.get("href")}
                    for tag in hreflang_tags
                ]
                
                # Extract structured data (JSON-LD)
                json_ld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, list):
                            result["structured_data"].extend(data)
                        else:
                            result["structured_data"].append(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Extract visible text content
                result["content"] = self._extract_text_content(soup)
                result["word_count"] = len(result["content"].split()) if result["content"] else 0
                
                # Save HTML snapshot
                snapshot_filename = self._generate_snapshot_filename(url)
                snapshot_path = os.path.join(self.snapshots_dir, snapshot_filename)
                with open(snapshot_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                result["html_snapshot_path"] = snapshot_path
                
                await browser.close()
                
        except Exception as e:
            logger.error("Crawl failed", url=url, error=str(e))
            result["error"] = str(e)
        
        return result
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract visible text content from HTML."""
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        # Get text
        text = soup.get_text(separator=" ", strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text[:50000]  # Limit content size
    
    def _generate_snapshot_filename(self, url: str) -> str:
        """Generate a filename for HTML snapshot."""
        parsed = urlparse(url)
        safe_path = re.sub(r'[^a-zA-Z0-9]', '_', parsed.path)[:50]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{parsed.netloc}_{safe_path}_{timestamp}.html"
    
    def extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract all links from HTML content."""
        soup = BeautifulSoup(html_content, "lxml")
        links = []
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            
            # Skip javascript and anchor links
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            
            # Only include HTTP(S) links
            if absolute_url.startswith(("http://", "https://")):
                links.append(absolute_url)
        
        return list(set(links))
    
    def is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        return urlparse(url1).netloc == urlparse(url2).netloc
    
    def is_allowed_path(self, url: str, allowed_paths: List[str], excluded_paths: List[str]) -> bool:
        """Check if URL path is allowed by the crawl configuration."""
        parsed = urlparse(url)
        path = parsed.path
        
        # Check excluded paths first
        for excluded in excluded_paths:
            if path.startswith(excluded):
                return False
        
        # If no allowed paths specified, allow all
        if not allowed_paths:
            return True
        
        # Check if path matches any allowed path
        for allowed in allowed_paths:
            if path.startswith(allowed):
                return True
        
        return False


# Singleton instance
crawler = CrawlerService()

