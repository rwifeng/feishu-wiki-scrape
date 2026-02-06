"""
Core scraper implementation for Feishu wiki pages
"""

import requests
from bs4 import BeautifulSoup
import html2text
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Set
import logging
import time


class FeishuWikiScraper:
    """
    A scraper for Feishu wiki pages that converts content to Markdown format.
    Similar to firecrawl, it can scrape entire wiki sites by following sidebar links.
    """

    def __init__(
        self,
        cookies: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        delay: float = 1.0,
    ):
        """
        Initialize the scraper.

        Args:
            cookies: Optional cookies for authentication
            headers: Optional custom headers
            delay: Delay between requests in seconds (default: 1.0)
        """
        self.session = requests.Session()
        self.delay = delay
        self.logger = logging.getLogger(__name__)

        # Set default headers
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

        # Update with custom headers if provided
        if headers:
            self.session.headers.update(headers)

        # Set cookies if provided
        if cookies:
            self.session.cookies.update(cookies)

        # Initialize html2text converter
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0  # Don't wrap text
        self.html2text.ignore_emphasis = False

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch a page and return BeautifulSoup object.

        Args:
            url: URL of the page to fetch

        Returns:
            BeautifulSoup object or None if fetch failed
        """
        try:
            self.logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, "lxml")
        except requests.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None

    def extract_sidebar_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract all wiki page links from the sidebar navigation.

        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute URLs found in the sidebar
        """
        links = set()

        # Look for common sidebar/navigation selectors in Feishu wiki pages
        # These selectors may need adjustment based on actual Feishu HTML structure
        sidebar_selectors = [
            "nav",
            ".sidebar",
            ".navigation",
            ".wiki-nav",
            ".toc",
            '[class*="sidebar"]',
            '[class*="nav"]',
            '[class*="menu"]',
        ]

        for selector in sidebar_selectors:
            sidebar_elements = soup.select(selector)
            for element in sidebar_elements:
                # Find all links in the sidebar
                for link in element.find_all("a", href=True):
                    href = link["href"]
                    # Convert relative URLs to absolute
                    absolute_url = urljoin(base_url, href)
                    # Only include wiki links from the same domain
                    if self._is_same_domain(absolute_url, base_url) and "/wiki/" in absolute_url:
                        links.add(absolute_url)

        # Also look for links in the main content that might be internal wiki links
        main_content = soup.find("main") or soup.find("article") or soup.find("body")
        if main_content:
            for link in main_content.find_all("a", href=True):
                href = link["href"]
                absolute_url = urljoin(base_url, href)
                if self._is_same_domain(absolute_url, base_url) and "/wiki/" in absolute_url:
                    links.add(absolute_url)

        return list(links)

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        return urlparse(url1).netloc == urlparse(url2).netloc

    def extract_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from the page.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            HTML content as string
        """
        # Try to find the main content area
        # Common selectors for main content in wiki pages
        content_selectors = [
            "main",
            "article",
            '[class*="content"]',
            '[class*="wiki-content"]',
            '[role="main"]',
            ".main-content",
        ]

        content = None
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                break

        # If no main content found, use body
        if not content:
            content = soup.find("body")

        if content:
            # Remove script and style elements
            for script in content(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            return str(content)

        return ""

    def html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to Markdown.

        Args:
            html_content: HTML content as string

        Returns:
            Markdown formatted string
        """
        try:
            markdown = self.html2text.handle(html_content)
            return markdown.strip()
        except Exception as e:
            self.logger.error(f"Error converting HTML to Markdown: {e}")
            return ""

    def scrape_page(self, url: str) -> Optional[Dict[str, str]]:
        """
        Scrape a single page and return its content as Markdown.

        Args:
            url: URL of the page to scrape

        Returns:
            Dictionary with 'url', 'title', and 'markdown' keys, or None if failed
        """
        soup = self.fetch_page(url)
        if not soup:
            return None

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else "Untitled"

        # Extract and convert content
        html_content = self.extract_content(soup)
        markdown = self.html_to_markdown(html_content)

        return {
            "url": url,
            "title": title,
            "markdown": markdown,
        }

    def scrape_wiki(
        self,
        start_url: str,
        max_pages: Optional[int] = None,
        include_sidebar: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Scrape an entire wiki site starting from a given URL.

        Args:
            start_url: Starting URL of the wiki
            max_pages: Maximum number of pages to scrape (None for unlimited)
            include_sidebar: Whether to follow sidebar links (default: True)

        Returns:
            List of dictionaries, each containing 'url', 'title', and 'markdown' for a page
        """
        visited: Set[str] = set()
        to_visit: List[str] = [start_url]
        results: List[Dict[str, str]] = []

        while to_visit and (max_pages is None or len(results) < max_pages):
            url = to_visit.pop(0)

            if url in visited:
                continue

            visited.add(url)

            # Scrape the page
            page_data = self.scrape_page(url)
            if page_data:
                results.append(page_data)
                self.logger.info(f"Scraped: {page_data['title']} ({len(results)} pages)")

                # Find more links if include_sidebar is True
                if include_sidebar and (max_pages is None or len(results) < max_pages):
                    soup = self.fetch_page(url)
                    if soup:
                        new_links = self.extract_sidebar_links(soup, url)
                        for link in new_links:
                            if link not in visited and link not in to_visit:
                                to_visit.append(link)
                                self.logger.debug(f"Added to queue: {link}")

            # Be polite with delays
            if to_visit:
                time.sleep(self.delay)

        self.logger.info(f"Scraping complete. Total pages: {len(results)}")
        return results

    def scrape_to_file(
        self,
        start_url: str,
        output_file: str,
        max_pages: Optional[int] = None,
        include_sidebar: bool = True,
    ):
        """
        Scrape wiki and save all content to a single Markdown file.

        Args:
            start_url: Starting URL of the wiki
            output_file: Path to output Markdown file
            max_pages: Maximum number of pages to scrape (None for unlimited)
            include_sidebar: Whether to follow sidebar links (default: True)
        """
        results = self.scrape_wiki(start_url, max_pages, include_sidebar)

        with open(output_file, "w", encoding="utf-8") as f:
            for i, page in enumerate(results):
                if i > 0:
                    f.write("\n\n---\n\n")
                f.write(f"# {page['title']}\n\n")
                f.write(f"Source: {page['url']}\n\n")
                f.write(page["markdown"])
                f.write("\n")

        self.logger.info(f"Saved {len(results)} pages to {output_file}")
