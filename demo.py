"""
Demo script showing various usage patterns of the Feishu Wiki Scraper
"""

from feishu_wiki_scrape import FeishuWikiScraper
import logging

print("=" * 70)
print("Feishu Wiki Scraper - Demo")
print("=" * 70)
print()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

print("1. Basic Initialization")
print("-" * 70)
scraper = FeishuWikiScraper()
print("✓ Created basic scraper with default settings")
print()

print("2. Initialization with Custom Settings")
print("-" * 70)
scraper_custom = FeishuWikiScraper(
    cookies={"session": "example_session_value"},
    headers={"Custom-Header": "value"},
    delay=2.0
)
print("✓ Created scraper with custom cookies, headers, and 2.0s delay")
print()

print("3. HTML to Markdown Conversion Demo")
print("-" * 70)
sample_html = """
<html>
<body>
    <h1>Welcome to Feishu Wiki</h1>
    <h2>Features</h2>
    <ul>
        <li><strong>Collaboration</strong>: Work together seamlessly</li>
        <li><strong>Documentation</strong>: Create beautiful docs</li>
        <li><strong>Knowledge Base</strong>: Organize information</li>
    </ul>
    <h2>Getting Started</h2>
    <p>To get started with Feishu Wiki:</p>
    <ol>
        <li>Create an account</li>
        <li>Start a new wiki</li>
        <li>Invite your team</li>
    </ol>
    <p>Learn more at <a href="https://www.feishu.cn">Feishu website</a>.</p>
</body>
</html>
"""

markdown = scraper.html_to_markdown(sample_html)
print("Input HTML:")
print(sample_html[:200] + "...")
print()
print("Output Markdown:")
print(markdown)
print()

print("4. Command-Line Usage Examples")
print("-" * 70)
print("Scrape a single page:")
print("  $ feishu-wiki-scrape https://example.feishu.cn/wiki/page")
print()
print("Scrape with authentication:")
print("  $ feishu-wiki-scrape https://example.feishu.cn/wiki/page \\")
print('      --cookies \'{"session": "your-session-id"}\'')
print()
print("Limit to 10 pages with custom delay:")
print("  $ feishu-wiki-scrape https://example.feishu.cn/wiki/page \\")
print("      --max-pages 10 --delay 2.0 -o output.md")
print()
print("Output as JSON:")
print("  $ feishu-wiki-scrape https://example.feishu.cn/wiki/page \\")
print("      --json-output > output.json")
print()

print("5. Python API Usage Examples")
print("-" * 70)
print("""
# Example 1: Scrape a single page
from feishu_wiki_scrape import FeishuWikiScraper

scraper = FeishuWikiScraper()
page = scraper.scrape_page("https://example.feishu.cn/wiki/page")

if page:
    print(f"Title: {page['title']}")
    print(f"Content: {page['markdown'][:200]}...")

# Example 2: Scrape entire wiki
results = scraper.scrape_wiki(
    start_url="https://example.feishu.cn/wiki/page",
    max_pages=50,
    include_sidebar=True
)

for page in results:
    print(f"{page['title']} - {page['url']}")

# Example 3: Save to file
scraper.scrape_to_file(
    start_url="https://example.feishu.cn/wiki/page",
    output_file="wiki_export.md"
)
""")
print()

print("6. Authentication Setup")
print("-" * 70)
print("""
To scrape authenticated Feishu wikis:

1. Open the Feishu wiki in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage > Cookies
4. Copy the cookie values (e.g., session_id, token, etc.)
5. Use them in your scraper:

   scraper = FeishuWikiScraper(
       cookies={
           "session_id": "your-session-id",
           "other_cookie": "other-value"
       }
   )

Or via CLI:

   feishu-wiki-scrape URL --cookies '{"session_id": "value"}'
""")
print()

print("7. Target URL for This Task")
print("-" * 70)
target_url = "https://zcn3fx96oxg4.feishu.cn/wiki/H5V5wMczPif5A5khSG3cWx65nbc"
print(f"Target URL: {target_url}")
print()
print("To scrape this wiki, run:")
print(f"  $ feishu-wiki-scrape {target_url} -o wiki_output.md")
print()
print("If authentication is required:")
print(f"  $ feishu-wiki-scrape {target_url} \\")
print('      --cookies \'{"session": "your-session-id"}\' \\')
print("      -o wiki_output.md")
print()

print("=" * 70)
print("✓ Demo completed successfully!")
print("=" * 70)
