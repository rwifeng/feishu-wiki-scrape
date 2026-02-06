"""
Integration test to verify multi-page wiki scraping works
"""

from feishu_wiki_scrape import FeishuWikiScraper
from bs4 import BeautifulSoup
from unittest.mock import Mock, patch
import logging

# Enable logging to see what's happening
logging.basicConfig(level=logging.INFO)


def test_multi_page_scraping():
    """Test that the scraper can follow links and scrape multiple pages"""
    
    scraper = FeishuWikiScraper()
    
    # Mock HTML responses for different pages
    page1_html = """
    <html>
        <head><title>Page 1 - Home</title></head>
        <body>
            <nav>
                <a href="/wiki/page2">Page 2</a>
                <a href="/wiki/page3">Page 3</a>
            </nav>
            <main>
                <h1>Welcome to Page 1</h1>
                <p>This is the home page.</p>
            </main>
        </body>
    </html>
    """
    
    page2_html = """
    <html>
        <head><title>Page 2 - Features</title></head>
        <body>
            <nav>
                <a href="/wiki/page1">Page 1</a>
                <a href="/wiki/page3">Page 3</a>
            </nav>
            <main>
                <h1>Page 2 Features</h1>
                <p>This page describes features.</p>
            </main>
        </body>
    </html>
    """
    
    page3_html = """
    <html>
        <head><title>Page 3 - About</title></head>
        <body>
            <nav>
                <a href="/wiki/page1">Page 1</a>
                <a href="/wiki/page2">Page 2</a>
            </nav>
            <main>
                <h1>About Us</h1>
                <p>This is the about page.</p>
            </main>
        </body>
    </html>
    """
    
    # Create a mock response function
    def mock_get(url, **kwargs):
        response = Mock()
        response.status_code = 200
        
        if url.endswith("/page1") or url == "https://example.feishu.cn/wiki/page1":
            response.content = page1_html.encode('utf-8')
        elif url.endswith("/page2") or url == "https://example.feishu.cn/wiki/page2":
            response.content = page2_html.encode('utf-8')
        elif url.endswith("/page3") or url == "https://example.feishu.cn/wiki/page3":
            response.content = page3_html.encode('utf-8')
        else:
            response.content = page1_html.encode('utf-8')
        
        response.raise_for_status = Mock()
        return response
    
    # Patch the session.get method
    with patch.object(scraper.session, 'get', side_effect=mock_get):
        # Scrape the wiki starting from page1
        results = scraper.scrape_wiki(
            start_url="https://example.feishu.cn/wiki/page1",
            max_pages=None,
            include_sidebar=True
        )
        
        # Should have scraped all 3 pages
        assert len(results) == 3, f"Expected 3 pages, found {len(results)}"
        
        # Check that all pages were scraped
        titles = [page['title'] for page in results]
        assert "Page 1 - Home" in titles, "Page 1 should be scraped"
        assert "Page 2 - Features" in titles, "Page 2 should be scraped"
        assert "Page 3 - About" in titles, "Page 3 should be scraped"
        
        # Check URLs
        urls = [page['url'] for page in results]
        assert any('page1' in url for url in urls), "page1 URL should be present"
        assert any('page2' in url for url in urls), "page2 URL should be present"
        assert any('page3' in url for url in urls), "page3 URL should be present"
        
        # Check that markdown content is present
        for page in results:
            assert len(page['markdown']) > 0, f"Page {page['title']} should have content"
            assert page['title'] != "Untitled", f"Page should have a proper title"
        
        print(f"✓ Multi-page scraping works - scraped {len(results)} pages")
        print(f"  Pages: {', '.join(titles)}")


def test_max_pages_limit():
    """Test that max_pages parameter limits the number of pages scraped"""
    
    scraper = FeishuWikiScraper()
    
    # Mock HTML with many links
    page_html_template = """
    <html>
        <head><title>Page {}</title></head>
        <body>
            <nav>
                <a href="/wiki/page1">Page 1</a>
                <a href="/wiki/page2">Page 2</a>
                <a href="/wiki/page3">Page 3</a>
                <a href="/wiki/page4">Page 4</a>
                <a href="/wiki/page5">Page 5</a>
            </nav>
            <main><h1>Page {} Content</h1></main>
        </body>
    </html>
    """
    
    def mock_get(url, **kwargs):
        response = Mock()
        response.status_code = 200
        
        # Extract page number from URL
        page_num = url.split('page')[-1]
        if not page_num.isdigit():
            page_num = "1"
        
        response.content = page_html_template.format(page_num, page_num).encode('utf-8')
        response.raise_for_status = Mock()
        return response
    
    with patch.object(scraper.session, 'get', side_effect=mock_get):
        # Scrape with max_pages limit
        results = scraper.scrape_wiki(
            start_url="https://example.feishu.cn/wiki/page1",
            max_pages=2,  # Only scrape 2 pages
            include_sidebar=True
        )
        
        # Should have scraped exactly 2 pages
        assert len(results) == 2, f"Expected 2 pages (due to max_pages), found {len(results)}"
        
        print(f"✓ max_pages limit works - scraped {len(results)} pages as expected")


def test_no_sidebar_mode():
    """Test that no-sidebar mode only scrapes the initial page"""
    
    scraper = FeishuWikiScraper()
    
    page_html = """
    <html>
        <head><title>Single Page</title></head>
        <body>
            <nav>
                <a href="/wiki/page2">Page 2</a>
                <a href="/wiki/page3">Page 3</a>
            </nav>
            <main><h1>Only this page should be scraped</h1></main>
        </body>
    </html>
    """
    
    def mock_get(url, **kwargs):
        response = Mock()
        response.status_code = 200
        response.content = page_html.encode('utf-8')
        response.raise_for_status = Mock()
        return response
    
    with patch.object(scraper.session, 'get', side_effect=mock_get):
        # Scrape with include_sidebar=False
        results = scraper.scrape_wiki(
            start_url="https://example.feishu.cn/wiki/page1",
            max_pages=None,
            include_sidebar=False  # Don't follow links
        )
        
        # Should have scraped only 1 page
        assert len(results) == 1, f"Expected 1 page (no sidebar mode), found {len(results)}"
        
        print("✓ No-sidebar mode works - scraped only the initial page")


def run_all_tests():
    """Run all integration tests"""
    print("Running integration tests...\n")
    
    tests = [
        test_multi_page_scraping,
        test_max_pages_limit,
        test_no_sidebar_mode,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n✓ All integration tests passed!")
    return True


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
