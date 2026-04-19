#!/usr/bin/env python3
"""
ArticleForge — Module entry point

Allows running the system via:
    python -m article_forge
    python -m article_forge --help

Or from anywhere if installed as a package.
"""

import sys
import argparse
from pathlib import Path

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from processing_ui import ArticleForgeCLi


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        prog="article-forge",
        description="ArticleForge - Professional PDF article processing and organization",
        epilog="Run without arguments to launch interactive CLI"
    )

    parser.add_argument(
        "--mode",
        choices=["cli", "process", "search", "export", "stats"],
        default="cli",
        help="Operation mode (default: interactive CLI)"
    )

    parser.add_argument(
        "--query",
        type=str,
        help="Search query (for --mode search)"
    )

    parser.add_argument(
        "--by",
        choices=["keyword", "author"],
        default="keyword",
        help="Search type (default: keyword)"
    )

    parser.add_argument(
        "--format",
        choices=["bibtex", "csv", "json"],
        default="bibtex",
        help="Export format (default: bibtex - recommended for Zotero)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview processing without saving"
    )

    parser.add_argument(
        "--batch",
        type=int,
        help="Process batch size for large collections"
    )

    args = parser.parse_args()

    # Launch CLI
    cli = ArticleForgeCLi()

    if args.mode == "cli":
        # Interactive mode
        cli.run()
    elif args.mode == "process":
        # Batch processing mode
        cli.menu_process_articles()
    elif args.mode == "search":
        # Search mode
        if not args.query:
            print("Error: --query required for search mode")
            sys.exit(1)
        cli.print_section(f"Search: {args.by}={args.query}")
        search_type = f"--by-{args.by}" if args.by else "--by-keyword"
        cli._run_query(f"{search_type} {args.query}")
    elif args.mode == "export":
        # Export mode
        cli.menu_export_data()
    elif args.mode == "stats":
        # Statistics mode
        cli.menu_statistics()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
