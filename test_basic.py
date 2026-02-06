"""
Simple test to verify the library works correctly
"""

def test_imports():
    """Test that all modules can be imported"""
    from feishu_wiki_scrape import FeishuWikiScraper
    from feishu_wiki_scrape.scraper import FeishuWikiScraper as ScraperClass
    from feishu_wiki_scrape.cli import main
    print("✓ All imports successful")


def test_scraper_initialization():
    """Test scraper can be initialized"""
    from feishu_wiki_scrape import FeishuWikiScraper
    
    scraper = FeishuWikiScraper()
    assert scraper is not None
    assert scraper.delay == 1.0
    
    scraper_with_options = FeishuWikiScraper(
        cookies={"test": "value"},
        headers={"Custom": "Header"},
        delay=2.0
    )
    assert scraper_with_options.delay == 2.0
    print("✓ Scraper initialization works")


def test_html_to_markdown():
    """Test HTML to Markdown conversion"""
    from feishu_wiki_scrape import FeishuWikiScraper
    
    scraper = FeishuWikiScraper()
    
    # Test basic HTML
    html = "<h1>Title</h1><p>Paragraph</p>"
    markdown = scraper.html_to_markdown(html)
    assert "Title" in markdown
    assert "Paragraph" in markdown
    
    # Test with links
    html_with_links = '<a href="http://example.com">Link</a>'
    markdown_with_links = scraper.html_to_markdown(html_with_links)
    assert "Link" in markdown_with_links
    assert "example.com" in markdown_with_links
    
    # Test with bold and italic
    html_with_formatting = "<strong>Bold</strong> and <em>italic</em>"
    markdown_with_formatting = scraper.html_to_markdown(html_with_formatting)
    assert "Bold" in markdown_with_formatting
    
    print("✓ HTML to Markdown conversion works")


def test_url_domain_check():
    """Test same domain checking"""
    from feishu_wiki_scrape import FeishuWikiScraper
    
    scraper = FeishuWikiScraper()
    
    url1 = "https://example.feishu.cn/wiki/page1"
    url2 = "https://example.feishu.cn/wiki/page2"
    url3 = "https://other.feishu.cn/wiki/page1"
    
    assert scraper._is_same_domain(url1, url2)
    assert not scraper._is_same_domain(url1, url3)
    
    print("✓ Domain checking works")


def test_content_extraction():
    """Test content extraction from HTML"""
    from feishu_wiki_scrape import FeishuWikiScraper
    from bs4 import BeautifulSoup
    
    scraper = FeishuWikiScraper()
    
    # Test with main tag
    html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <nav>Navigation</nav>
            <main>
                <h1>Main Content</h1>
                <p>This is the main content.</p>
            </main>
            <footer>Footer</footer>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "lxml")
    content = scraper.extract_content(soup)
    assert "Main Content" in content
    assert "main content" in content.lower()
    # Navigation and footer should be removed
    assert "Navigation" not in content and "<nav" not in content
    
    print("✓ Content extraction works")


def run_all_tests():
    """Run all tests"""
    print("Running tests...\n")
    
    tests = [
        test_imports,
        test_scraper_initialization,
        test_html_to_markdown,
        test_url_domain_check,
        test_content_extraction,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n✓ All tests passed!")
    return True


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
