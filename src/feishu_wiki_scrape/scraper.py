"""
Core scraper implementation for Feishu wiki pages
"""

import requests
from bs4 import BeautifulSoup
import html2text
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Dict, List, Optional, Set, Any
from collections import deque
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
        timeout: float = 30.0,
        max_redirects: int = 5,
    ):
        """
        Initialize the scraper.

        Args:
            cookies: Optional cookies for authentication
            headers: Optional custom headers
            delay: Delay between requests in seconds (default: 1.0)
            timeout: Request timeout in seconds (default: 30.0)
            max_redirects: Maximum number of redirects to follow (default: 5)
        """
        self.session = requests.Session()
        self.delay = delay
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

        # Set max redirects for security
        self.session.max_redirects = max_redirects

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
            response = self.session.get(url, timeout=self.timeout, verify=True)
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

        # First, try to find links in sidebar elements
        for selector in sidebar_selectors:
            sidebar_elements = soup.select(selector)
            if sidebar_elements:
                for element in sidebar_elements:
                    # Find all links in the sidebar
                    for link in element.find_all("a", href=True):
                        href = link["href"]
                        # Convert relative URLs to absolute
                        absolute_url = urljoin(base_url, href)
                        # Normalize URL to avoid duplicates
                        normalized_url = self._normalize_url(absolute_url)
                        # Only include wiki links from the same domain
                        if self._is_same_domain(normalized_url, base_url) and "/wiki/" in normalized_url:
                            links.add(normalized_url)
        
        # If no sidebar links found, fall back to searching the entire page
        # This helps when the HTML structure doesn't match expected selectors
        if not links:
            self.logger.debug("No sidebar links found, searching entire page for wiki links")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                # Normalize URL to avoid duplicates
                normalized_url = self._normalize_url(absolute_url)
                # Only include wiki links from the same domain
                if self._is_same_domain(normalized_url, base_url) and "/wiki/" in normalized_url:
                    links.add(normalized_url)

        return list(links)

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        return urlparse(url1).netloc == urlparse(url2).netloc

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by removing fragments and sorting query parameters.
        This helps avoid scraping the same page multiple times.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL string
        """
        parsed = urlparse(url)
        # Remove fragment and reconstruct URL
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        return normalized

    def _validate_url(self, url: str) -> bool:
        """
        Validate that the URL is properly formatted.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            # Check basic URL structure
            if not parsed.scheme or not parsed.netloc:
                self.logger.error(f"Invalid URL format: {url}")
                return False
            return True
        except Exception as e:
            self.logger.error(f"Error validating URL {url}: {e}")
            return False

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
        except Exception:
            self.logger.exception("Error converting HTML to Markdown")
            return ""

    def scrape_page(self, url: str, soup: Optional[BeautifulSoup] = None) -> Optional[Dict[str, str]]:
        """
        Scrape a single page and return its content as Markdown.

        Args:
            url: URL of the page to scrape
            soup: Optional pre-fetched BeautifulSoup object to avoid re-fetching

        Returns:
            Dictionary with 'url', 'title', and 'markdown' keys (and internal '_soup' key), 
            or None if failed
        """
        # Validate URL
        if not self._validate_url(url):
            return None
            
        # Fetch page if not provided
        if soup is None:
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
            "_soup": soup,  # Internal use only, not part of public API
        }

    def _extract_metadata(self, url: str, soup: BeautifulSoup, title: str) -> Dict[str, Any]:
        """
        Extract metadata from a page for Firecrawl-compatible format.
        
        Args:
            url: Page URL
            soup: BeautifulSoup object
            title: Page title
            
        Returns:
            Dictionary with metadata fields
        """
        metadata = {
            "url": url,
            "title": title,
            "sourceURL": url,
            "statusCode": 200,  # Assumed success if we got here
        }
        
        # Extract meta tags
        meta_tags = soup.find_all("meta")
        for meta in meta_tags:
            name = meta.get("name", "").lower()
            property_attr = meta.get("property", "").lower()
            content = meta.get("content", "")
            
            if name == "keywords":
                metadata["keywords"] = content
            elif name == "description" or property_attr == "og:description":
                metadata["description"] = content
            elif property_attr == "og:type":
                metadata["ogType"] = content
            elif property_attr == "og:image":
                metadata["ogImage"] = content
                
        # Try to detect language
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata["language"] = html_tag.get("lang")
        
        # Set content type
        metadata["contentType"] = "text/html; charset=utf-8"
        
        return metadata

    def scrape_page_with_metadata(self, url: str, soup: Optional[BeautifulSoup] = None) -> Optional[Dict[str, Any]]:
        """
        Scrape a single page and return its content with metadata in Firecrawl-compatible format.

        Args:
            url: URL of the page to scrape
            soup: Optional pre-fetched BeautifulSoup object to avoid re-fetching

        Returns:
            Dictionary with 'markdown' and 'metadata' keys, or None if failed
        """
        # Validate URL
        if not self._validate_url(url):
            return None
            
        # Fetch page if not provided
        if soup is None:
            soup = self.fetch_page(url)
        
        if not soup:
            return None

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text().strip() if title_tag else "Untitled"

        # Extract and convert content
        html_content = self.extract_content(soup)
        markdown = self.html_to_markdown(html_content)
        
        # Extract metadata
        metadata = self._extract_metadata(url, soup, title)

        return {
            "markdown": markdown,
            "metadata": metadata,
            "_soup": soup,  # Internal use only
        }

    def format_pages_to_markdown(self, results: List[Dict[str, str]]) -> str:
        """
        Format a list of page results into a single Markdown string.
        
        Args:
            results: List of page dictionaries with 'title', 'url', and 'markdown' keys
            
        Returns:
            Formatted Markdown string
        """
        output = []
        for i, page in enumerate(results):
            if i > 0:
                output.append("\n\n---\n\n")
            output.append(f"# {page['title']}\n\n")
            output.append(f"Source: {page['url']}\n\n")
            output.append(page["markdown"])
            output.append("\n")
        return "".join(output)

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
        # Normalize the start URL
        start_url = self._normalize_url(start_url)
        
        visited: Set[str] = set()
        to_visit_queue: deque = deque([start_url])
        to_visit_set: Set[str] = {start_url}  # For O(1) membership checking
        results: List[Dict[str, str]] = []

        try:
            while to_visit_queue and (max_pages is None or len(results) < max_pages):
                url = to_visit_queue.popleft()
                to_visit_set.discard(url)

                if url in visited:
                    continue

                visited.add(url)

                # Scrape the page
                page_data = self.scrape_page(url)
                if page_data:
                    # Extract soup for internal use and remove from results
                    soup = page_data.pop("_soup", None)
                    # Now append to results without _soup
                    results.append(page_data)
                    self.logger.info(f"Scraped: {page_data['title']} ({len(results)} pages)")

                    # Find more links if include_sidebar is True
                    if include_sidebar and (max_pages is None or len(results) < max_pages):
                        if soup:
                            new_links = self.extract_sidebar_links(soup, url)
                            for link in new_links:
                                # Normalize link before checking
                                normalized_link = self._normalize_url(link)
                                if normalized_link not in visited and normalized_link not in to_visit_set:
                                    to_visit_queue.append(normalized_link)
                                    to_visit_set.add(normalized_link)
                                    self.logger.debug(f"Added to queue: {normalized_link}")

                # Be polite with delays
                if to_visit_queue:
                    time.sleep(self.delay)
        except KeyboardInterrupt:
            self.logger.info(
                "Scraping interrupted by user. Returning results collected so far."
            )

        self.logger.info(f"Scraping complete. Total pages: {len(results)}")
        return results

    def format_as_firecrawl(
        self,
        results: List[Dict[str, Any]],
        start_url: str,
        status: str = "completed",
    ) -> Dict[str, Any]:
        """
        Format scraping results in Firecrawl-compatible JSON format.
        
        Accepts results from either scrape_wiki() or scrape_wiki_with_metadata().
        
        Args:
            results: List of page dictionaries. Can be either:
                     - Simple format: {'url', 'title', 'markdown'} from scrape_wiki()
                     - Full format: {'markdown', 'metadata'} from scrape_wiki_with_metadata()
            start_url: The starting URL that was scraped
            status: Status of the scraping operation (default: "completed")
            
        Returns:
            Dictionary in Firecrawl-compatible format with success, status, data, etc.
        """
        data = []
        for page in results:
            # Check if this is already in full metadata format
            if "metadata" in page:
                # Already has metadata, use as-is
                data.append({
                    "markdown": page.get("markdown", ""),
                    "metadata": page["metadata"]
                })
            else:
                # Convert simple format to Firecrawl format with basic metadata
                data.append({
                    "markdown": page.get("markdown", ""),
                    "metadata": {
                        "url": page.get("url", ""),
                        "title": page.get("title", "Untitled"),
                        "sourceURL": page.get("url", ""),
                        "statusCode": 200,
                        "contentType": "text/html; charset=utf-8",
                    }
                })
        
        return {
            "success": True,
            "status": status,
            "completed": len(results),
            "total": len(results),
            "data": data,
        }

    def scrape_wiki_with_metadata(
        self,
        start_url: str,
        max_pages: Optional[int] = None,
        include_sidebar: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Scrape an entire wiki site with full metadata in Firecrawl-compatible format.

        Args:
            start_url: Starting URL of the wiki
            max_pages: Maximum number of pages to scrape (None for unlimited)
            include_sidebar: Whether to follow sidebar links (default: True)

        Returns:
            List of dictionaries with 'markdown' and 'metadata' keys
        """
        # Normalize the start URL
        start_url = self._normalize_url(start_url)
        
        visited: Set[str] = set()
        to_visit_queue: deque = deque([start_url])
        to_visit_set: Set[str] = {start_url}
        results: List[Dict[str, Any]] = []

        try:
            while to_visit_queue and (max_pages is None or len(results) < max_pages):
                url = to_visit_queue.popleft()
                to_visit_set.discard(url)

                if url in visited:
                    continue

                visited.add(url)

                # Scrape the page with metadata
                page_data = self.scrape_page_with_metadata(url)
                if page_data:
                    # Extract soup for internal use
                    soup = page_data.pop("_soup", None)
                    results.append(page_data)
                    title = page_data.get("metadata", {}).get("title", "Untitled")
                    self.logger.info(f"Scraped: {title} ({len(results)} pages)")

                    # Find more links if include_sidebar is True
                    if include_sidebar and (max_pages is None or len(results) < max_pages):
                        if soup:
                            new_links = self.extract_sidebar_links(soup, url)
                            for link in new_links:
                                normalized_link = self._normalize_url(link)
                                if normalized_link not in visited and normalized_link not in to_visit_set:
                                    to_visit_queue.append(normalized_link)
                                    to_visit_set.add(normalized_link)
                                    self.logger.debug(f"Added to queue: {normalized_link}")

                # Be polite with delays
                if to_visit_queue:
                    time.sleep(self.delay)
        except KeyboardInterrupt:
            self.logger.info(
                "Scraping interrupted by user. Returning results collected so far."
            )

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

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(self.format_pages_to_markdown(results))
            self.logger.info(f"Saved {len(results)} pages to {output_file}")
        except OSError as e:
            self.logger.error(f"Failed to write output file '{output_file}': {e}")
            raise
