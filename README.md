# Feishu Wiki Scraper

A Python library to scrape Feishu (飞书) wiki pages and convert them to Markdown format, similar to [Firecrawl](https://firecrawl.dev/). This tool can scrape entire wiki sites by following sidebar links and extracting all content.

## Features

- 🚀 Scrape single Feishu wiki pages or entire wiki sites
- 📝 Convert HTML content to clean Markdown format
- 🔗 Automatically follow sidebar links to scrape related pages
- 🍪 Support for authentication via cookies and custom headers
- ⚙️ Configurable scraping options (delays, max pages, etc.)
- 💾 Export to Markdown files or JSON format
- 📂 **Directory output mode** — save each page as a separate `.md` file preserving wiki tree structure
- 🎯 Command-line interface for easy usage
- 🔥 **Firecrawl-compatible JSON output with metadata**

## Installation

### From source

```bash
git clone https://github.com/rwifeng/feishu-wiki-scrape.git
cd feishu-wiki-scrape
pip install -e .
```

### Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Basic usage to scrape a Feishu wiki:

```bash
# Save to a single Markdown file
feishu-wiki-scrape https://zcn3fx96oxg4.feishu.cn/wiki/H5V5wMczPif5A5khSG3cWx65nbc -o output.md

# Save as a directory tree (one .md file per page, preserving wiki structure)
feishu-wiki-scrape https://zcn3fx96oxg4.feishu.cn/wiki/H5V5wMczPif5A5khSG3cWx65nbc -o ./wiki-docs/
```

#### Options

- `-o, --output`: Output path (default: `output.md`). If the path ends with `/`, is an existing directory, or has no file extension, each page is saved as a separate `.md` file in a nested directory tree matching the wiki structure
- `--max-pages`: Maximum number of pages to scrape (default: unlimited)
- `--no-sidebar`: Don't follow sidebar links (scrape only the given URL)
- `--delay`: Delay between requests in seconds (default: 1.0)
- `--cookies`: Cookies as JSON string for authentication
- `--headers`: Custom headers as JSON string
- `--json-output`: Output as JSON instead of Markdown file
- `--firecrawl-format`: Output in Firecrawl-compatible JSON format with metadata
- `-v, --verbose`: Enable verbose logging

#### Examples

Scrape a single page without following links:
```bash
feishu-wiki-scrape https://example.feishu.cn/wiki/page --no-sidebar -o single_page.md
```

Scrape with authentication cookies:
```bash
feishu-wiki-scrape https://example.feishu.cn/wiki/page \
  --cookies '{"session_id": "your-session-id"}' \
  -o authenticated_output.md
```

Limit to 10 pages with custom delay:
```bash
feishu-wiki-scrape https://example.feishu.cn/wiki/page \
  --max-pages 10 \
  --delay 2.0 \
  -o limited_output.md
```

Output as JSON:
```bash
feishu-wiki-scrape https://example.feishu.cn/wiki/page --json-output > output.json
```

Save as directory tree preserving wiki structure:
```bash
feishu-wiki-scrape https://example.feishu.cn/wiki/page -o ./docs/
```

This produces a directory tree like:
```
docs/
  🚀 Introduction/
    index.md          # parent page with children
    Getting Started.md
  FAQ/
    index.md
    Common Errors.md
  Claude.md           # leaf page (no children)
```

### Python API

```python
from feishu_wiki_scrape import FeishuWikiScraper

# Create scraper instance
scraper = FeishuWikiScraper(
    cookies={"session_id": "your-session-id"},  # Optional
    headers={"Custom-Header": "value"},          # Optional
    delay=1.0                                    # Delay between requests
)

# Scrape a single page
page = scraper.scrape_page("https://example.feishu.cn/wiki/page")
print(page["title"])
print(page["markdown"])

# Scrape entire wiki (follows sidebar links)
results = scraper.scrape_wiki(
    start_url="https://example.feishu.cn/wiki/page",
    max_pages=50,           # Optional: limit number of pages
    include_sidebar=True    # Follow sidebar links
)

for page in results:
    print(f"Title: {page['title']}")
    print(f"URL: {page['url']}")
    print(f"Content:\n{page['markdown']}\n")

# Save to file
scraper.scrape_to_file(
    start_url="https://example.feishu.cn/wiki/page",
    output_file="output.md",
    max_pages=None,         # No limit
    include_sidebar=True
)

# Save to directory tree (preserves wiki sidebar structure)
count = scraper.scrape_wiki_to_directory(
    start_url="https://example.feishu.cn/wiki/page",
    output_dir="./docs/",
    max_pages=None          # No limit
)
print(f"Saved {count} pages")
```

### Firecrawl-Compatible Output

This library supports Firecrawl-compatible JSON output with rich metadata, making it easy to build API-compatible tools.

#### Using CLI

```bash
feishu-wiki-scrape https://example.feishu.cn/wiki/page \
  --firecrawl-format \
  --max-pages 10 > output.json
```

Output format:
```json
{
  "success": true,
  "status": "completed",
  "completed": 10,
  "total": 10,
  "data": [
    {
      "markdown": "# Page Title\n\nPage content...",
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
    }
  ]
}
```

#### Using Python API

```python
from feishu_wiki_scrape import FeishuWikiScraper

scraper = FeishuWikiScraper()

# Scrape with metadata
results = scraper.scrape_wiki_with_metadata(
    start_url="https://example.feishu.cn/wiki/page",
    max_pages=10,
    include_sidebar=True
)

# Format as Firecrawl response (automatically handles metadata format)
firecrawl_response = scraper.format_as_firecrawl(results, start_url)

print(firecrawl_response)
```

For a complete example of building a Firecrawl-compatible API, see `example_firecrawl.py`.

## How It Works

1. **Page Fetching**: Uses `requests` to fetch wiki pages with configurable headers and cookies
2. **Content Extraction**: Parses HTML with `BeautifulSoup` to extract main content area
3. **Link Discovery**: Finds all wiki links in sidebars and navigation elements
4. **Markdown Conversion**: Converts HTML to clean Markdown using `html2text`
5. **Crawling**: Follows links breadth-first to scrape entire wiki sites
6. **Rate Limiting**: Respects configurable delays between requests

## Authentication

Feishu wikis may require authentication. You can provide cookies or headers:

### Getting Cookies

1. Open the Feishu wiki in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage > Cookies
4. Copy the relevant cookie values
5. Pass them using `--cookies` option or in Python code

Example:
```bash
feishu-wiki-scrape https://example.feishu.cn/wiki/page \
  --cookies '{"session_id": "abc123", "other_cookie": "value"}'
```

## Output Format

### Single Markdown File (`-o output.md`)

Pages are separated by horizontal rules (`---`) with each page containing:
- Page title as H1 heading
- Source URL
- Markdown content

### Directory Tree (`-o dir/`)

Each wiki page is saved as a separate `.md` file. The directory structure mirrors the wiki's sidebar tree:

- **Pages with children** become a directory containing `index.md` (the page content) plus child pages
- **Leaf pages** (no children) are saved as `{title}.md` in the parent directory
- The wiki space root container is skipped so the output directory maps directly to the top-level pages

### JSON Format

```json
[
  {
    "url": "https://example.feishu.cn/wiki/page1",
    "title": "Page Title",
    "markdown": "# Content\n\nPage content in markdown..."
  },
  {
    "url": "https://example.feishu.cn/wiki/page2",
    "title": "Another Page",
    "markdown": "# Content\n\nMore content..."
  }
]
```

## Troubleshooting

### Pages not loading
- Check if authentication is required (try with cookies)
- Verify the URL is accessible in a browser
- Increase delay between requests

### Missing content
- Some content may be loaded dynamically with JavaScript
- Try using cookies from an authenticated session
- Check verbose output with `-v` flag

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.