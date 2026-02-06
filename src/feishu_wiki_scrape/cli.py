"""
Command-line interface for Feishu Wiki Scraper
"""

import argparse
import json
import logging
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
        help="Output file path (default: output.md)",
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
        # Scrape the wiki
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
            # Output as JSON
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
