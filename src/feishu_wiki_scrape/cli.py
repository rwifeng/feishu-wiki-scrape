"""
Command-line interface for Feishu Wiki Scraper
"""

import argparse
import json
import logging
import os
import sys
from .scraper import FeishuWikiScraper


def setup_logging(verbose: bool):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def validate_positive_float(value):
    """Validate that a value is a positive float."""
    try:
        fvalue = float(value)
        if fvalue <= 0:
            raise argparse.ArgumentTypeError(f"{value} must be a positive number")
        return fvalue
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value} is not a valid number")


def _is_directory_output(path: str) -> bool:
    """
    Determine whether the output path should be treated as a directory.
    True if the path ends with '/', is an existing directory, or has no
    file extension (e.g. './tmp', 'output_dir').
    """
    if path.endswith('/') or path.endswith(os.sep):
        return True
    if os.path.isdir(path):
        return True
    # No file extension → treat as directory
    _, ext = os.path.splitext(os.path.basename(path))
    if not ext:
        return True
    return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape Feishu wiki pages and convert to Markdown"
    )
    parser.add_argument("url", help="Starting URL of the Feishu wiki")
    parser.add_argument(
        "-o",
        "--output",
        default="output.md",
        help="Output file path (default: output.md). If path ends with '/' it saves as a directory tree with one .md file per page.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to scrape (default: unlimited)",
    )
    parser.add_argument(
        "--no-sidebar",
        action="store_true",
        help="Don't follow sidebar links (scrape only the given URL)",
    )
    parser.add_argument(
        "--delay",
        type=validate_positive_float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--cookies",
        type=str,
        help='Cookies as JSON string (e.g., \'{"session": "value"}\')',
    )
    parser.add_argument(
        "--headers",
        type=str,
        help='Custom headers as JSON string (e.g., \'{"Authorization": "Bearer token"}\')',
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output as JSON instead of Markdown file",
    )
    parser.add_argument(
        "--firecrawl-format",
        action="store_true",
        help="Output in Firecrawl-compatible JSON format with metadata",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Parse cookies and headers if provided
    cookies = None
    if args.cookies:
        try:
            cookies = json.loads(args.cookies)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for cookies", file=sys.stderr)
            return 1

    headers = None
    if args.headers:
        try:
            headers = json.loads(args.headers)
        except json.JSONDecodeError:
            print("Error: Invalid JSON format for headers", file=sys.stderr)
            return 1

    # Create scraper instance
    scraper = FeishuWikiScraper(cookies=cookies, headers=headers, delay=args.delay)

    try:
        # Scrape the wiki with appropriate format
        if args.firecrawl_format:
            # Use metadata-enhanced scraping for Firecrawl format
            results_with_metadata = scraper.scrape_wiki_with_metadata(
                start_url=args.url,
                max_pages=args.max_pages,
                include_sidebar=not args.no_sidebar,
            )
            
            if not results_with_metadata:
                print("No pages scraped. Check the URL and authentication.", file=sys.stderr)
                return 1
            
            # Format as Firecrawl response (automatically handles metadata format)
            firecrawl_response = scraper.format_as_firecrawl(results_with_metadata, args.url)
            
            # Always output as JSON for Firecrawl format
            print(json.dumps(firecrawl_response, indent=2, ensure_ascii=False))
        elif _is_directory_output(args.output):
            # Directory mode: save each page as a separate .md file in tree structure
            count = scraper.scrape_wiki_to_directory(
                start_url=args.url,
                output_dir=args.output,
                max_pages=args.max_pages,
            )
            if count == 0:
                print("No pages scraped. Check the URL and authentication.", file=sys.stderr)
                return 1
            print(f"Successfully scraped {count} pages to {args.output}")
        else:
            # Standard scraping
            results = scraper.scrape_wiki(
                start_url=args.url,
                max_pages=args.max_pages,
                include_sidebar=not args.no_sidebar,
            )

            if not results:
                print("No pages scraped. Check the URL and authentication.", file=sys.stderr)
                return 1

            # Output results
            if args.json_output:
                # Output as simple JSON
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                # Save to Markdown file
                try:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(scraper.format_pages_to_markdown(results))
                    print(f"Successfully scraped {len(results)} pages to {args.output}")
                except OSError as e:
                    print(f"Error writing to output file '{args.output}': {e}", file=sys.stderr)
                    return 1

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
