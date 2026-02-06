"""
Example: Building a Firecrawl-compatible tool with feishu-wiki-scrape

This example demonstrates how to create a tool that outputs Feishu wiki 
scraping results in Firecrawl-compatible JSON format.
"""

from feishu_wiki_scrape import FeishuWikiScraper
import json

# Example URL (replace with actual Feishu wiki URL)
url = "https://zcn3fx96oxg4.feishu.cn/wiki/H5V5wMczPif5A5khSG3cWx65nbc"

print("=" * 80)
print("Firecrawl-Compatible Feishu Wiki Scraper Example")
print("=" * 80)
print()

# Initialize scraper with authentication if needed
scraper = FeishuWikiScraper(
    cookies={
        # Add your Feishu cookies here if authentication is required
        # "session": "your-session-id",
    },
    delay=1.0  # Be respectful with delays
)

print("Method 1: Using scrape_wiki_with_metadata() for full control")
print("-" * 80)

# Scrape wiki with metadata (limit to 3 pages for demo)
results_with_metadata = scraper.scrape_wiki_with_metadata(
    start_url=url,
    max_pages=3,
    include_sidebar=True
)

print(f"Scraped {len(results_with_metadata)} pages")
print()
print("Example output structure:")
print(json.dumps(results_with_metadata[0] if results_with_metadata else {}, indent=2)[:500] + "...")
print()

# Format as Firecrawl response
if results_with_metadata:
    # Convert to simple format first for format_as_firecrawl
    simple_results = [
        {
            "url": r["metadata"]["url"],
            "title": r["metadata"]["title"],
            "markdown": r["markdown"]
        }
        for r in results_with_metadata
    ]
    
    firecrawl_response = scraper.format_as_firecrawl(simple_results, url)
    # Replace data with full metadata version
    firecrawl_response["data"] = results_with_metadata
    
    print("Firecrawl-compatible response structure:")
    print(f"  success: {firecrawl_response['success']}")
    print(f"  status: {firecrawl_response['status']}")
    print(f"  completed: {firecrawl_response['completed']}")
    print(f"  total: {firecrawl_response['total']}")
    print(f"  data[0] keys: {list(firecrawl_response['data'][0].keys())}")
    print(f"  metadata fields: {list(firecrawl_response['data'][0]['metadata'].keys())}")
    print()

print()
print("Method 2: Using CLI with --firecrawl-format flag")
print("-" * 80)
print("Command:")
print(f"  feishu-wiki-scrape {url} --firecrawl-format --max-pages 3")
print()
print("This will output JSON in the following format:")
print("""
{
  "success": true,
  "status": "completed",
  "completed": 3,
  "total": 3,
  "data": [
    {
      "markdown": "# Page Title\\n\\nPage content...",
      "metadata": {
        "url": "https://example.feishu.cn/wiki/page",
        "title": "Page Title",
        "keywords": "keyword1, keyword2",
        "language": "zh-CN",
        "sourceURL": "https://example.feishu.cn/wiki/page",
        "statusCode": 200,
        "contentType": "text/html; charset=utf-8",
        "description": "Page description"
      }
    },
    ...
  ]
}
""")

print()
print("Method 3: Building a simple API wrapper")
print("-" * 80)
print("""
from flask import Flask, jsonify, request
from feishu_wiki_scrape import FeishuWikiScraper

app = Flask(__name__)
scraper = FeishuWikiScraper(delay=1.0)

@app.route('/v1/crawl', methods=['POST'])
def crawl():
    data = request.json
    url = data.get('url')
    max_pages = data.get('max_pages', 10)
    
    # Scrape with metadata
    results = scraper.scrape_wiki_with_metadata(
        start_url=url,
        max_pages=max_pages,
        include_sidebar=True
    )
    
    # Format response
    simple_results = [
        {"url": r["metadata"]["url"], 
         "title": r["metadata"]["title"], 
         "markdown": r["markdown"]}
        for r in results
    ]
    response = scraper.format_as_firecrawl(simple_results, url)
    response["data"] = results
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(port=3002)
""")

print()
print("=" * 80)
print("For more information, see the README.md")
print("=" * 80)
