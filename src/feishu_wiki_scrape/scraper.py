"""
Core scraper implementation for Feishu wiki pages
"""

import os
import re
import requests
from bs4 import BeautifulSoup
import html2text
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Dict, List, Optional, Set, Any, Tuple
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
        First tries Feishu API, then falls back to HTML parsing.

        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute URLs found in the sidebar
        """
        # First try the Feishu wiki tree API
        if 'feishu.cn' in base_url or 'larksuite.com' in base_url:
            api_links = self.extract_feishu_wiki_links(soup, base_url)
            if api_links:
                return api_links
            self.logger.warning("Feishu API failed, falling back to HTML parsing")

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
                    # Normalize URL to avoid duplicates
                    normalized_url = self._normalize_url(absolute_url)
                    # Only include wiki links from the same domain
                    if self._is_same_domain(normalized_url, base_url) and "/wiki/" in normalized_url:
                        links.add(normalized_url)

        # Also extract wiki links from page content (for Feishu pages with internal links)
        content_links = self._extract_content_wiki_links(soup, base_url)
        links.update(content_links)

        return list(links)

    def _extract_content_wiki_links(self, soup: BeautifulSoup, base_url: str) -> Set[str]:
        """
        Extract wiki links from the main page content.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
            
        Returns:
            Set of wiki page URLs found in content
        """
        import re
        links = set()
        parsed_base = urlparse(base_url)
        
        # Find all links in the page that point to wiki pages
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Handle both absolute and relative URLs
            if '/wiki/' in href:
                absolute_url = urljoin(base_url, href)
                normalized_url = self._normalize_url(absolute_url)
                if self._is_same_domain(normalized_url, base_url):
                    links.add(normalized_url)
        
        # Also look for wiki tokens in scripts (for dynamically loaded content)
        wiki_token_pattern = re.compile(r'["\']?wiki_token["\']?\s*[:=]\s*["\']([A-Za-z0-9]+)["\']')
        obj_token_pattern = re.compile(r'["\']?obj_token["\']?\s*[:=]\s*["\']([A-Za-z0-9]+)["\']')
        
        for script in soup.find_all('script'):
            script_text = script.string or ''
            
            for match in wiki_token_pattern.finditer(script_text):
                token = match.group(1)
                url = f"{parsed_base.scheme}://{parsed_base.netloc}/wiki/{token}"
                links.add(url)
                
            for match in obj_token_pattern.finditer(script_text):
                token = match.group(1)
                # Only add if it looks like a wiki token (24+ chars)
                if len(token) >= 20:
                    url = f"{parsed_base.scheme}://{parsed_base.netloc}/wiki/{token}"
                    links.add(url)
        
        return links

    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        return urlparse(url1).netloc == urlparse(url2).netloc

    def _extract_wiki_token(self, url: str) -> Optional[str]:
        """
        Extract wiki token from Feishu URL.
        
        Args:
            url: Feishu wiki URL
            
        Returns:
            Wiki token string or None
        """
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')
        # URL format: /wiki/{wiki_token}
        if 'wiki' in path_parts:
            wiki_index = path_parts.index('wiki')
            if wiki_index + 1 < len(path_parts):
                return path_parts[wiki_index + 1]
        return None

    def _extract_space_id_from_page(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract space_id from page HTML or scripts.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Space ID string or None
        """
        import re
        import json
        
        # Look for space_id in script tags
        for script in soup.find_all('script'):
            script_text = script.string or ''
            
            # Try to find space_id in various formats
            # Pattern 1: "space_id":"xxxxx" or 'space_id':'xxxxx'
            match = re.search(r'["\']space_id["\']:\s*["\'](\d+)["\']', script_text)
            if match:
                return match.group(1)
            
            # Pattern 2: spaceId: "xxxxx" or spaceId: 'xxxxx'
            match = re.search(r'spaceId:\s*["\'](\d+)["\']', script_text)
            if match:
                return match.group(1)
            
            # Pattern 3: "spaceId":"xxxxx"
            match = re.search(r'["\']spaceId["\']:\s*["\'](\d+)["\']', script_text)
            if match:
                return match.group(1)
                
        return None

    def _fetch_wiki_tree(self, base_url: str, space_id: str, wiki_token: str) -> List[str]:
        """
        Fetch wiki tree from Feishu API to get all page links.
        
        Args:
            base_url: Base URL of the Feishu domain
            space_id: Space ID
            wiki_token: Wiki token of the starting page
            
        Returns:
            List of wiki page URLs
        """
        parsed = urlparse(base_url)
        api_url = f"{parsed.scheme}://{parsed.netloc}/space/api/wiki/v2/tree/get_info/"
        
        params = {
            'space_id': space_id,
            'with_space': 'true',
            'with_perm': 'true',
            'expand_shortcut': 'true',
            'need_shared': 'true',
            'exclude_fields': '5',
            'with_deleted': 'true',
            'wiki_token': wiki_token,
        }
        
        try:
            self.logger.info(f"Fetching wiki tree from API: {api_url}")
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Log the response for debugging
            self.logger.debug(f"Wiki tree API response: {data}")
            
            # Check for API error (e.g., login required)
            code = data.get('code')
            if code is not None and code != 0:
                self.logger.warning(f"Wiki tree API error: code={code}, msg={data.get('msg')}. Authentication may be required.")
                return []
            
            # Store raw tree data for directory mode
            self._last_tree_data = data
            self._last_tree_parsed = urlparse(base_url)
            
            # Extract all wiki tokens from the tree
            urls = self._parse_wiki_tree(data, parsed.scheme, parsed.netloc)
            self.logger.info(f"Found {len(urls)} pages in wiki tree")
            return urls
            
        except requests.RequestException as e:
            self.logger.warning(f"Failed to fetch wiki tree API: {e}")
            return []
        except (ValueError, KeyError) as e:
            self.logger.warning(f"Failed to parse wiki tree response: {e}")
            return []

    def _parse_wiki_tree(self, data: Dict, scheme: str, netloc: str) -> List[str]:
        """
        Parse wiki tree API response to extract all page URLs.
        
        Args:
            data: API response data
            scheme: URL scheme (http/https)
            netloc: Domain name
            
        Returns:
            List of wiki page URLs
        """
        urls = []
        seen_tokens = set()
        
        def add_token(token: str):
            """Add a wiki token as URL if not already seen."""
            if token and token not in seen_tokens:
                seen_tokens.add(token)
                url = f"{scheme}://{netloc}/wiki/{token}"
                urls.append(url)
        
        # Navigate to the tree data
        tree_data = data.get('data', {}).get('tree', {})
        if not tree_data:
            # Fallback to old method if structure is different
            return self._parse_wiki_tree_fallback(data, scheme, netloc)
        
        # Extract from root_list (list of wiki_token strings)
        root_list = tree_data.get('root_list', [])
        for token in root_list:
            if isinstance(token, str):
                add_token(token)
        
        # Extract from child_map (dict mapping parent to list of child tokens)
        child_map = tree_data.get('child_map', {})
        for parent_token, children in child_map.items():
            add_token(parent_token)
            for child_token in children:
                if isinstance(child_token, str):
                    add_token(child_token)
        
        # Extract from nodes (dict mapping wiki_token to node details)
        nodes = tree_data.get('nodes', {})
        for token, node_info in nodes.items():
            add_token(token)
            # Also get the url if available
            if isinstance(node_info, dict):
                node_url = node_info.get('url', '')
                if node_url and '/wiki/' in node_url:
                    # Extract token from URL
                    url_token = node_url.split('/wiki/')[-1].split('?')[0].split('#')[0]
                    add_token(url_token)
        
        return urls

    def _parse_wiki_tree_structure(self, data: Dict, scheme: str, netloc: str) -> Dict[str, Any]:
        """
        Parse wiki tree API response and preserve the full tree structure.
        
        Returns:
            Dictionary with:
                'root_list': list of root token strings
                'child_map': dict mapping parent_token -> [child_tokens]
                'nodes': dict mapping token -> {'title': str, 'url': str, ...}
                'space_name': optional space name string
        """
        tree_data = data.get('data', {}).get('tree', {})
        if not tree_data:
            return {'root_list': [], 'child_map': {}, 'nodes': {}, 'space_name': ''}
        
        root_list = tree_data.get('root_list', [])
        child_map = dict(tree_data.get('child_map', {}))  # mutable copy
        raw_nodes = tree_data.get('nodes', {})
        
        # Try to extract space name
        space_name = ''
        space_info = data.get('data', {}).get('space', {})
        if isinstance(space_info, dict):
            space_name = space_info.get('name', '') or space_info.get('space_name', '')
        
        nodes = {}
        for token, node_info in raw_nodes.items():
            if isinstance(node_info, dict):
                title = node_info.get('title', '') or node_info.get('name', '') or token
                nodes[token] = {
                    'title': title,
                    'url': f"{scheme}://{netloc}/wiki/{token}",
                    'obj_token': node_info.get('obj_token', ''),
                    'obj_type': node_info.get('obj_type', ''),
                    'has_child': node_info.get('has_child', False),
                    'parent_wiki_token': node_info.get('parent_wiki_token', ''),
                }
        
        # Rebuild child_map from parent_wiki_token if child_map is incomplete
        # This fixes the case where the API returns nodes with parent info
        # but doesn't fully populate child_map for deeper levels
        for token, node in nodes.items():
            parent = node.get('parent_wiki_token', '')
            if parent:
                if parent not in child_map:
                    child_map[parent] = []
                if token not in child_map[parent]:
                    child_map[parent].append(token)
        
        self.logger.debug(f"Tree structure: {len(nodes)} nodes, {len(child_map)} parents in child_map, roots={root_list}")
        
        return {
            'root_list': root_list,
            'child_map': child_map,
            'nodes': nodes,
            'space_name': space_name,
        }
    
    def _parse_wiki_tree_fallback(self, data: Dict, scheme: str, netloc: str) -> List[str]:
        """
        Fallback method for parsing wiki tree with unknown structure.
        
        Args:
            data: API response data
            scheme: URL scheme (http/https)
            netloc: Domain name
            
        Returns:
            List of wiki page URLs
        """
        urls = []
        
        def extract_nodes(node):
            """Recursively extract wiki tokens from tree nodes."""
            if isinstance(node, dict):
                # Check for wiki_token or obj_token
                wiki_token = node.get('wiki_token') or node.get('obj_token') or node.get('token')
                if wiki_token:
                    url = f"{scheme}://{netloc}/wiki/{wiki_token}"
                    if url not in urls:
                        urls.append(url)
                
                # Check for children
                children = node.get('children') or node.get('nodes') or node.get('items') or []
                for child in children:
                    extract_nodes(child)
                    
                # Also check for tree/data/nodes structures
                for key in ['tree', 'data', 'nodes', 'wiki_nodes', 'space_info']:
                    if key in node:
                        extract_nodes(node[key])
                        
            elif isinstance(node, list):
                for item in node:
                    extract_nodes(item)
        
        extract_nodes(data)
        return urls

    def extract_feishu_wiki_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract wiki page links using Feishu API.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL of the wiki
            
        Returns:
            List of wiki page URLs
        """
        wiki_token = self._extract_wiki_token(base_url)
        space_id = self._extract_space_id_from_page(soup)
        
        if wiki_token and space_id:
            self.logger.info(f"Found space_id: {space_id}, wiki_token: {wiki_token}")
            return self._fetch_wiki_tree(base_url, space_id, wiki_token)
        else:
            self.logger.warning(f"Could not extract space_id ({space_id}) or wiki_token ({wiki_token})")
            return []

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

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """
        Sanitize a string for use as a filename.
        Removes or replaces characters that are invalid in file paths.
        """
        # Replace path separators and other problematic chars
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        # Collapse multiple underscores/spaces
        name = re.sub(r'_+', '_', name).strip('_ ')
        # Fallback if empty
        return name or 'Untitled'

    def _get_wiki_tree_structure(self, start_url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and return the wiki tree structure with parent-child relationships.
        Recursively expands subtrees for nodes that have children but aren't
        fully represented in child_map.
        
        Args:
            start_url: Starting URL of the wiki
            
        Returns:
            Tree structure dict or None if API fails
        """
        soup = self.fetch_page(start_url)
        if not soup:
            return None
        
        wiki_token = self._extract_wiki_token(start_url)
        space_id = self._extract_space_id_from_page(soup)
        
        if not wiki_token or not space_id:
            self.logger.warning("Could not extract space_id or wiki_token for tree structure")
            return None
        
        parsed = urlparse(start_url)
        api_url = f"{parsed.scheme}://{parsed.netloc}/space/api/wiki/v2/tree/get_info/"
        
        params = {
            'space_id': space_id,
            'with_space': 'true',
            'with_perm': 'true',
            'expand_shortcut': 'true',
            'need_shared': 'true',
            'exclude_fields': '5',
            'with_deleted': 'true',
            'wiki_token': wiki_token,
        }
        
        try:
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            code = data.get('code')
            if code is not None and code != 0:
                self.logger.warning(f"Wiki tree API error: code={code}")
                return None
            
            tree_info = self._parse_wiki_tree_structure(data, parsed.scheme, parsed.netloc)
            
            # Recursively expand nodes that claim to have children
            # but whose children are not yet in child_map
            self._expand_incomplete_subtrees(
                tree_info, api_url, space_id, parsed.scheme, parsed.netloc
            )
            
            return tree_info
        except Exception as e:
            self.logger.warning(f"Failed to get wiki tree structure: {e}")
            return None

    def _expand_incomplete_subtrees(
        self,
        tree_info: Dict[str, Any],
        api_url: str,
        space_id: str,
        scheme: str,
        netloc: str,
    ):
        """
        For nodes with has_child=True that are not in child_map,
        fetch their subtree from the API and merge into tree_info.
        """
        nodes = tree_info['nodes']
        child_map = tree_info['child_map']
        
        # Find nodes that claim children but have no entries in child_map
        to_expand = []
        for token, node in nodes.items():
            if node.get('has_child') and token not in child_map:
                to_expand.append(token)
        
        if not to_expand:
            return
        
        self.logger.info(f"Expanding {len(to_expand)} subtrees with missing children...")
        
        for token in to_expand:
            try:
                time.sleep(self.delay * 0.5)  # lighter delay for API calls
                params = {
                    'space_id': space_id,
                    'with_space': 'false',
                    'with_perm': 'true',
                    'expand_shortcut': 'true',
                    'need_shared': 'true',
                    'exclude_fields': '5',
                    'with_deleted': 'true',
                    'wiki_token': token,
                }
                response = self.session.get(api_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                
                code = data.get('code')
                if code is not None and code != 0:
                    continue
                
                sub_tree = self._parse_wiki_tree_structure(data, scheme, netloc)
                
                # Merge child_map
                for parent, children in sub_tree['child_map'].items():
                    if parent not in child_map:
                        child_map[parent] = []
                    for child in children:
                        if child not in child_map[parent]:
                            child_map[parent].append(child)
                
                # Merge nodes
                for t, node_info in sub_tree['nodes'].items():
                    if t not in nodes:
                        nodes[t] = node_info
                
                self.logger.debug(f"Expanded subtree for {token}: +{len(sub_tree['nodes'])} nodes")
                
            except Exception as e:
                self.logger.debug(f"Failed to expand subtree for {token}: {e}")

    def _compute_tree_paths(self, tree_info: Dict[str, Any], skip_root: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Compute the directory path segments for each wiki token based on tree structure.
        
        Args:
            tree_info: Tree structure from _parse_wiki_tree_structure()
            skip_root: Optional token whose level should be omitted from paths
                       (e.g., the space root container)
            
        Returns:
            Dict mapping wiki_token -> list of path segment strings (titles)
            e.g. {'tokenA': ['RootTitle'], 'tokenB': ['RootTitle', 'ChildTitle']}
        """
        root_list = tree_info['root_list']
        child_map = tree_info['child_map']
        nodes = tree_info['nodes']
        
        # Build parent map from child_map
        parent_map: Dict[str, Optional[str]] = {}
        for parent_token, children in child_map.items():
            for child_token in children:
                parent_map[child_token] = parent_token
        
        # Supplement with parent_wiki_token from node data
        for token, node in nodes.items():
            parent = node.get('parent_wiki_token', '')
            if parent and token not in parent_map:
                parent_map[token] = parent
        
        # Roots have no parent
        for root_token in root_list:
            if root_token not in parent_map:
                parent_map[root_token] = None
        
        def get_title(token: str) -> str:
            node = nodes.get(token)
            if node:
                return self._sanitize_filename(node.get('title', '') or token)
            return self._sanitize_filename(token)
        
        def get_path_segments(token: str) -> List[str]:
            """Walk up the tree to build path from root to this node."""
            segments = []
            current = token
            visited = set()
            while current is not None and current not in visited:
                visited.add(current)
                # Skip the space root level if requested
                if current != skip_root:
                    segments.append(get_title(current))
                current = parent_map.get(current)
            segments.reverse()
            return segments
        
        paths = {}
        for token in nodes:
            segs = get_path_segments(token)
            if segs:  # Only add if there are segments after skipping root
                paths[token] = segs
        
        return paths

    def scrape_wiki_to_directory(
        self,
        start_url: str,
        output_dir: str,
        max_pages: Optional[int] = None,
    ) -> int:
        """
        Scrape wiki and save each page as a separate .md file preserving tree structure.
        
        Pages with children become directories with an index.md inside.
        The directory hierarchy mirrors the wiki's sidebar tree.
        
        Args:
            start_url: Starting URL of the wiki
            output_dir: Root output directory
            max_pages: Maximum number of pages to scrape (None for unlimited)
            
        Returns:
            Number of pages saved
        """
        start_url = self._normalize_url(start_url)
        
        # Step 1: Get tree structure
        tree_info = self._get_wiki_tree_structure(start_url)
        
        if tree_info and tree_info['nodes']:
            return self._scrape_with_tree(start_url, output_dir, tree_info, max_pages)
        else:
            # Fallback: flat scrape without tree (no API access / not a feishu site)
            self.logger.warning("Could not get tree structure, falling back to flat directory output")
            return self._scrape_flat_directory(start_url, output_dir, max_pages)

    def _scrape_with_tree(
        self,
        start_url: str,
        output_dir: str,
        tree_info: Dict[str, Any],
        max_pages: Optional[int],
    ) -> int:
        """
        Scrape pages using known tree structure, saving into nested directories.
        """
        nodes = tree_info['nodes']
        child_map = tree_info['child_map']
        root_list = tree_info['root_list']
        
        # Detect space root container: a token that is parent of root_list items
        # in child_map but is NOT itself in root_list.  This is the wiki space
        # wrapper node; the user's -o dir should map to this level.
        skip_root = None
        
        # Strategy 1: single-element root_list with no title
        if len(root_list) == 1:
            root_token = root_list[0]
            root_node = nodes.get(root_token, {})
            root_title = root_node.get('title', '')
            if not root_title or root_title == root_token:
                skip_root = root_token
        
        # Strategy 2: find a token that contains root_list items as children
        # but is NOT itself in root_list (the space-level wrapper)
        if not skip_root and root_list:
            root_set = set(root_list)
            for parent_token, children in child_map.items():
                if parent_token not in root_set and root_set.issubset(set(children)):
                    skip_root = parent_token
                    break
        
        if skip_root:
            self.logger.info(f"Skipping space root container: {skip_root}")
        
        token_paths = self._compute_tree_paths(tree_info, skip_root=skip_root)
        
        # Determine which tokens have children (they become directories)
        tokens_with_children = set()
        for parent_token, children in child_map.items():
            if children:
                tokens_with_children.add(parent_token)
        # Also mark parents discovered via parent_wiki_token
        for token, node in nodes.items():
            parent = node.get('parent_wiki_token', '')
            if parent and parent in nodes:
                tokens_with_children.add(parent)
        
        # Collect all tokens via BFS, then append any orphans from nodes
        all_tokens = []
        seen = set()
        queue = deque(root_list)
        while queue:
            token = queue.popleft()
            if token in seen:
                continue
            seen.add(token)
            all_tokens.append(token)
            for child in child_map.get(token, []):
                queue.append(child)
        
        # Add any nodes NOT reached by BFS (orphans from incomplete child_map)
        for token in nodes:
            if token not in seen:
                all_tokens.append(token)
                seen.add(token)
        
        os.makedirs(output_dir, exist_ok=True)
        count = 0
        
        for token in all_tokens:
            if max_pages is not None and count >= max_pages:
                break
            
            # Skip the space root container itself (don't scrape it)
            if token == skip_root:
                continue
            
            node = nodes.get(token, {})
            url = node.get('url', '')
            if not url:
                continue
            
            # Scrape the page
            page_data = self.scrape_page(url)
            if not page_data:
                continue
            
            page_data.pop('_soup', None)
            title = self._sanitize_filename(page_data.get('title', '') or node.get('title', '') or 'Untitled')
            markdown_content = f"# {page_data['title']}\n\nSource: {page_data['url']}\n\n{page_data['markdown']}\n"
            
            # Build file path from tree path
            path_segments = token_paths.get(token, [title])
            if not path_segments:
                path_segments = [title]
            
            if token in tokens_with_children:
                # This node has children: create dir and save as index.md
                dir_path = os.path.join(output_dir, *path_segments)
                os.makedirs(dir_path, exist_ok=True)
                file_path = os.path.join(dir_path, 'index.md')
            else:
                # Leaf node: save as title.md inside parent directory
                if len(path_segments) > 1:
                    parent_dir = os.path.join(output_dir, *path_segments[:-1])
                else:
                    parent_dir = output_dir
                os.makedirs(parent_dir, exist_ok=True)
                file_path = os.path.join(parent_dir, f"{path_segments[-1]}.md")
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                count += 1
                self.logger.info(f"Saved: {file_path} ({count} pages)")
            except OSError as e:
                self.logger.error(f"Failed to write {file_path}: {e}")
            
            # Be polite
            time.sleep(self.delay)
        
        self.logger.info(f"Scraping complete. Saved {count} pages to {output_dir}")
        return count

    def _scrape_flat_directory(
        self,
        start_url: str,
        output_dir: str,
        max_pages: Optional[int],
    ) -> int:
        """
        Fallback: scrape pages and save them flat in a single directory.
        """
        results = self.scrape_wiki(
            start_url=start_url,
            max_pages=max_pages,
            include_sidebar=True,
        )
        
        os.makedirs(output_dir, exist_ok=True)
        count = 0
        
        for page in results:
            title = self._sanitize_filename(page.get('title', 'Untitled'))
            file_path = os.path.join(output_dir, f"{title}.md")
            
            # Avoid overwriting: append number if needed
            base_path = file_path
            i = 1
            while os.path.exists(file_path):
                file_path = base_path.replace('.md', f'_{i}.md')
                i += 1
            
            markdown_content = f"# {page['title']}\n\nSource: {page['url']}\n\n{page['markdown']}\n"
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                count += 1
                self.logger.info(f"Saved: {file_path}")
            except OSError as e:
                self.logger.error(f"Failed to write {file_path}: {e}")
        
        self.logger.info(f"Saved {count} pages to {output_dir}")
        return count
