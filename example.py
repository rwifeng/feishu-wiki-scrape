"""
Example usage of the Feishu Wiki Scraper library
"""

from feishu_wiki_scrape import FeishuWikiScraper
import logging

# Enable logging to see progress
logging.basicConfig(level=logging.INFO)

# Example 1: Scrape a single page
print("Example 1: Scraping a single page")
print("-" * 50)

scraper = FeishuWikiScraper(delay=1.0)

# Note: This URL might require authentication
url = "https://zcn3fx96oxg4.feishu.cn/wiki/H5V5wMczPif5A5khSG3cWx65nbc"

page = scraper.scrape_page(url)
if page:
    print(f"Title: {page['title']}")
    print(f"URL: {page['url']}")
    print(f"Content preview: {page['markdown'][:200]}...")
else:
    print("Failed to scrape page. It might require authentication.")

print("\n")

# Example 2: Scrape entire wiki (with authentication if needed)
print("Example 2: Scraping entire wiki")
print("-" * 50)

# If authentication is needed, provide cookies
# You can get these from your browser's developer tools
cookies = {
    # "session_id": "your-session-id-here",
    # Add other required cookies
}

scraper_with_auth = FeishuWikiScraper(
    cookies=cookies if cookies else None,
    delay=1.0
)

# Scrape up to 5 pages
results = scraper_with_auth.scrape_wiki(
    start_url=url,
    max_pages=5,
    include_sidebar=True
)

print(f"Scraped {len(results)} pages")
for i, page in enumerate(results, 1):
    print(f"{i}. {page['title']} - {page['url']}")

# Example 3: Save to file
print("\n")
print("Example 3: Saving to file")
print("-" * 50)

output_file = "feishu_wiki_output.md"
scraper.scrape_to_file(
    start_url=url,
    output_file=output_file,
    max_pages=3,
    include_sidebar=False  # Only scrape the main page
)
print(f"Content saved to {output_file}")
