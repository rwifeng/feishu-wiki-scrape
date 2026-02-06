"""
Test for improved link extraction functionality
"""

from bs4 import BeautifulSoup
from feishu_wiki_scrape import FeishuWikiScraper


def test_sidebar_link_extraction():
    """Test that sidebar links are extracted correctly"""
    scraper = FeishuWikiScraper()
    
    # HTML with sidebar containing wiki links
    html = """
    <html>
        <body>
            <nav class="sidebar">
                <a href="/wiki/page1">Page 1</a>
                <a href="/wiki/page2">Page 2</a>
                <a href="/wiki/page3">Page 3</a>
            </nav>
            <main>
                <a href="https://external.com">External Link</a>
            </main>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html, "lxml")
    base_url = "https://example.feishu.cn/wiki/home"
    links = scraper.extract_sidebar_links(soup, base_url)
    
    # Should find 3 wiki links
    assert len(links) == 3, f"Expected 3 links, found {len(links)}"
    
    # All links should be absolute URLs
    for link in links:
        assert link.startswith("https://"), f"Link should be absolute: {link}"
        assert "/wiki/" in link, f"Link should contain /wiki/: {link}"
    
    print("✓ Sidebar link extraction works")


def test_fallback_link_extraction():
    """Test that fallback extracts all wiki links when no sidebar is found"""
    scraper = FeishuWikiScraper()
    
    # HTML without sidebar, but with wiki links in the page
    html = """
    <html>
        <body>
            <div class="content">
                <h1>Wiki Page</h1>
                <div class="links">
                    <a href="/wiki/pageA">Page A</a>
                    <a href="/wiki/pageB">Page B</a>
                    <a href="/wiki/pageC">Page C</a>
                    <a href="https://external.com">External</a>
                </div>
            </div>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html, "lxml")
    base_url = "https://example.feishu.cn/wiki/home"
    links = scraper.extract_sidebar_links(soup, base_url)
    
    # Should find 3 wiki links even without sidebar
    assert len(links) == 3, f"Expected 3 links with fallback, found {len(links)}"
    
    # All should be wiki links
    for link in links:
        assert "/wiki/" in link, f"Link should contain /wiki/: {link}"
    
    print("✓ Fallback link extraction works")


def test_no_duplicate_links():
    """Test that duplicate links are not added multiple times"""
    scraper = FeishuWikiScraper()
    
    # HTML with duplicate links
    html = """
    <html>
        <body>
            <nav>
                <a href="/wiki/page1">Page 1</a>
                <a href="/wiki/page1">Page 1 Again</a>
                <a href="/wiki/page2">Page 2</a>
            </nav>
            <div>
                <a href="/wiki/page1">Page 1 Third Time</a>
            </div>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html, "lxml")
    base_url = "https://example.feishu.cn/wiki/home"
    links = scraper.extract_sidebar_links(soup, base_url)
    
    # Should find only 2 unique links
    assert len(links) == 2, f"Expected 2 unique links, found {len(links)}"
    
    print("✓ Duplicate link filtering works")


def test_cross_domain_filtering():
    """Test that links from different domains are filtered out"""
    scraper = FeishuWikiScraper()
    
    html = """
    <html>
        <body>
            <div>
                <a href="/wiki/page1">Same Domain Page 1</a>
                <a href="https://example.feishu.cn/wiki/page2">Same Domain Page 2</a>
                <a href="https://other.feishu.cn/wiki/page3">Different Domain</a>
                <a href="https://external.com/wiki/page4">External Domain</a>
            </div>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html, "lxml")
    base_url = "https://example.feishu.cn/wiki/home"
    links = scraper.extract_sidebar_links(soup, base_url)
    
    # Should find only 2 links from the same domain
    assert len(links) == 2, f"Expected 2 same-domain links, found {len(links)}"
    
    for link in links:
        assert "example.feishu.cn" in link, f"Link should be from example.feishu.cn: {link}"
    
    print("✓ Cross-domain filtering works")


def test_url_normalization():
    """Test that URLs with fragments are normalized"""
    scraper = FeishuWikiScraper()
    
    html = """
    <html>
        <body>
            <nav>
                <a href="/wiki/page1#section1">Page 1 Section 1</a>
                <a href="/wiki/page1#section2">Page 1 Section 2</a>
                <a href="/wiki/page1">Page 1 No Fragment</a>
                <a href="/wiki/page2">Page 2</a>
            </nav>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html, "lxml")
    base_url = "https://example.feishu.cn/wiki/home"
    links = scraper.extract_sidebar_links(soup, base_url)
    
    # Should find only 2 unique links (page1 and page2)
    # Fragments should be removed
    assert len(links) == 2, f"Expected 2 links after normalization, found {len(links)}"
    
    # No link should contain a fragment
    for link in links:
        assert "#" not in link, f"Link should not contain fragment: {link}"
    
    print("✓ URL normalization works")


def run_all_tests():
    """Run all link extraction tests"""
    print("Running link extraction tests...\n")
    
    tests = [
        test_sidebar_link_extraction,
        test_fallback_link_extraction,
        test_no_duplicate_links,
        test_cross_domain_filtering,
        test_url_normalization,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n✓ All link extraction tests passed!")
    return True


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
