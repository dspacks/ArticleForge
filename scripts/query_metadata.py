#!/usr/bin/env python3
"""
Query and display metadata from the articles registry.

Usage:
    python query_metadata.py --list              # List all articles
    python query_metadata.py --by-keyword data   # Find articles by keyword
    python query_metadata.py --by-author Smith   # Find articles by author
    python query_metadata.py --stats             # Show statistics
    python query_metadata.py --export csv        # Export as CSV
"""

import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict
from collections import Counter

from config import METADATA_REGISTRY


def load_registry() -> Dict:
    """Load metadata registry."""
    if not METADATA_REGISTRY.exists():
        print(f"Error: Metadata registry not found at {METADATA_REGISTRY}")
        return {"articles": []}

    try:
        with open(METADATA_REGISTRY, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Error: Could not parse metadata registry")
        return {"articles": []}


def print_article(article: Dict, index: int = None) -> None:
    """Pretty print a single article entry."""
    if index:
        print(f"\n[{index}]")
    print(f"  Title:    {article.get('title', 'N/A')}")
    print(f"  Author:   {article.get('author', 'N/A')}")
    print(f"  Date:     {article.get('date', 'N/A')}")
    print(f"  Source:   {article.get('source', 'N/A')}")
    print(f"  File:     {article.get('output_file', 'N/A')}")

    keywords = article.get('keywords', [])
    if keywords:
        keywords_str = ", ".join(keywords)
        print(f"  Keywords: {keywords_str}")

    print(f"  Length:   {article.get('text_length', 'N/A')} chars")


def list_all(registry: Dict) -> None:
    """List all articles."""
    articles = registry.get('articles', [])

    if not articles:
        print("No articles in registry.")
        return

    print(f"\n{'=' * 80}")
    print(f"ALL ARTICLES ({len(articles)} total)")
    print(f"{'=' * 80}")

    for i, article in enumerate(articles, 1):
        print_article(article, i)

    print(f"\n{'=' * 80}")


def list_needs_editing(registry: Dict) -> None:
    """List articles that need manual metadata editing."""
    articles = registry.get('articles', [])

    needs_editing = []
    for article in articles:
        if not article.get('author'):
            needs_editing.append(article)

    if not needs_editing:
        print("\n✓ All articles have author metadata!")
        return

    print(f"\n{'=' * 80}")
    print(f"ARTICLES NEEDING MANUAL EDITING ({len(needs_editing)} total)")
    print(f"{'=' * 80}")
    print(f"\nThese articles are missing author information and need manual fixes:\n")

    for i, article in enumerate(needs_editing, 1):
        print(f"[{i}] {article.get('title', 'Unknown')}")
        print(f"    File: {article.get('output_file', 'N/A')}")
        print(f"    Date: {article.get('date', 'N/A')}")
        print()

    print(f"{'=' * 80}")
    print(f"\n📝 HOW TO FIX:")
    print(f"1. Open: metadata/manual_metadata_overrides.json")
    print(f"2. Add entries with author information, e.g.:")
    print(f"   {{\n     \"2026-02-10_HBR_Article_Title.md\": {{\n       \"author\": \"Author Name\"\n     }}\n   }}")
    print(f"3. Re-run the system to apply overrides")
    print(f"{'=' * 80}")


def find_by_keyword(registry: Dict, keyword: str) -> None:
    """Find articles containing a keyword."""
    articles = registry.get('articles', [])
    results = []

    keyword_lower = keyword.lower()

    for article in articles:
        keywords = [k.lower() for k in article.get('keywords', [])]
        title_lower = article.get('title', '').lower()

        if keyword_lower in keywords or keyword_lower in title_lower:
            results.append(article)

    if not results:
        print(f"No articles found with keyword: {keyword}")
        return

    print(f"\n{'=' * 80}")
    print(f"ARTICLES WITH KEYWORD: {keyword} ({len(results)} found)")
    print(f"{'=' * 80}")

    for i, article in enumerate(results, 1):
        print_article(article, i)


def find_by_author(registry: Dict, author: str) -> None:
    """Find articles by author."""
    articles = registry.get('articles', [])

    # Check for articles with missing author data
    missing_authors = [a for a in articles if not a.get('author')]
    if missing_authors:
        print(f"\n⚠ Note: {len(missing_authors)} article(s) have missing author data.")
        print(f"  These articles need manual editing:")
        for article in missing_authors:
            print(f"    - {article.get('title', 'Unknown')}")
        print(f"  To fix: Edit metadata/manual_metadata_overrides.json and add authors")
        print(f"{'=' * 80}\n")

    results = [a for a in articles if author.lower() in (a.get('author') or '').lower()]

    if not results:
        print(f"No articles found by author: {author}")
        return

    print(f"\n{'=' * 80}")
    print(f"ARTICLES BY AUTHOR: {author} ({len(results)} found)")
    print(f"{'=' * 80}")

    for i, article in enumerate(results, 1):
        print_article(article, i)


def show_stats(registry: Dict) -> None:
    """Show metadata statistics."""
    articles = registry.get('articles', [])

    if not articles:
        print("No articles in registry.")
        return

    print(f"\n{'=' * 80}")
    print("METADATA STATISTICS")
    print(f"{'=' * 80}")

    print(f"\nTotal Articles: {len(articles)}")

    # Sources
    sources = [a.get('source') for a in articles if a.get('source')]
    if sources:
        print(f"Article Sources:")
        source_counts = Counter(sources)
        for source, count in source_counts.most_common():
            print(f"  - {source}: {count} article(s)")

    # Authors
    authors = [a.get('author') for a in articles if a.get('author')]
    missing_authors = [a for a in articles if not a.get('author')]

    print(f"Unique Authors: {len(set(authors))}")
    if authors:
        print("  Top authors:")
        author_counts = Counter(authors)
        for author, count in author_counts.most_common(5):
            print(f"    - {author}: {count} article(s)")

    if missing_authors:
        print(f"\n⚠ Articles with Missing Authors: {len(missing_authors)}")
        for article in missing_authors:
            print(f"  - {article.get('title', 'Unknown')} ({article.get('output_file', 'N/A')})")
        print(f"  👉 To fix: Edit metadata/manual_metadata_overrides.json")

    # Date range
    dates = [a.get('date') for a in articles if a.get('date')]
    if dates:
        dates_sorted = sorted(dates)
        print(f"\nDate Range: {dates_sorted[0]} to {dates_sorted[-1]}")

    # Keywords
    all_keywords = []
    for a in articles:
        all_keywords.extend(a.get('keywords', []))

    if all_keywords:
        print(f"\nTotal Keywords: {len(all_keywords)}")
        print("  Top keywords:")
        keyword_counts = Counter(all_keywords)
        for keyword, count in keyword_counts.most_common(15):
            print(f"    - {keyword}: {count} article(s)")

    # Text length
    lengths = [a.get('text_length', 0) for a in articles]
    avg_length = sum(lengths) / len(lengths) if lengths else 0
    print(f"\nAverage Article Length: {avg_length:.0f} characters")

    # Processing dates
    processed = [a.get('processed_date') for a in articles if a.get('processed_date')]
    if processed:
        print(f"Articles Processed: {len(processed)}")

    print(f"\n{'=' * 80}")


def export_csv(registry: Dict, output_path: Path = None) -> None:
    """Export registry to CSV."""
    if not output_path:
        output_path = METADATA_REGISTRY.parent / 'articles_export.csv'

    articles = registry.get('articles', [])

    if not articles:
        print("No articles to export.")
        return

    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Prepare fieldnames
            fieldnames = ['title', 'author', 'date', 'source', 'output_file', 'keywords', 'text_length']

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for article in articles:
                row = {
                    'title': article.get('title', ''),
                    'author': article.get('author', ''),
                    'date': article.get('date', ''),
                    'source': article.get('source', ''),
                    'output_file': article.get('output_file', ''),
                    'keywords': '; '.join(article.get('keywords', [])),
                    'text_length': article.get('text_length', ''),
                }
                writer.writerow(row)

        print(f"\n✓ Exported {len(articles)} articles to {output_path}")

    except IOError as e:
        print(f"✗ Error writing CSV: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Query article metadata registry")

    parser.add_argument('--list', action='store_true', help='List all articles')
    parser.add_argument('--by-keyword', type=str, help='Find articles by keyword')
    parser.add_argument('--by-author', type=str, help='Find articles by author')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--needs-editing', action='store_true', help='Show articles needing manual metadata fixes')
    parser.add_argument('--export', type=str, choices=['csv', 'json'], help='Export registry')

    args = parser.parse_args()

    registry = load_registry()

    if args.list:
        list_all(registry)
    elif args.by_keyword:
        find_by_keyword(registry, args.by_keyword)
    elif args.by_author:
        find_by_author(registry, args.by_author)
    elif args.stats:
        show_stats(registry)
    elif args.needs_editing:
        list_needs_editing(registry)
    elif args.export:
        if args.export == 'csv':
            export_csv(registry)
        elif args.export == 'json':
            output_path = METADATA_REGISTRY.parent / 'articles_export.json'
            try:
                with open(output_path, 'w') as f:
                    json.dump(registry, f, indent=2)
                print(f"✓ Exported to {output_path}")
            except IOError as e:
                print(f"✗ Error: {e}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
