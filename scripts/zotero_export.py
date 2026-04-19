#!/usr/bin/env python3
"""
Zotero Export Module

Exports articles from the metadata registry to Zotero reference manager.
Supports both local Zotero library export and API integration.

Usage:
    python zotero_export.py --list              # Show exportable articles
    python zotero_export.py --export all        # Export all articles
    python zotero_export.py --export keyword    # Export by keyword
"""

import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from config import METADATA_REGISTRY


def load_articles() -> List[Dict]:
    """Load articles from metadata registry."""
    if not METADATA_REGISTRY.exists():
        print(f"Error: Metadata registry not found at {METADATA_REGISTRY}")
        return []

    try:
        with open(METADATA_REGISTRY, 'r') as f:
            data = json.load(f)
            return data.get('articles', [])
    except json.JSONDecodeError:
        print("Error: Could not parse metadata registry")
        return []


def format_for_zotero(article: Dict) -> Dict:
    """
    Format article metadata for Zotero import.

    Creates a Zotero-compatible entry with all relevant fields.

    Args:
        article: Article metadata from registry

    Returns:
        Zotero-formatted dictionary
    """
    zotero_entry = {
        'itemType': 'journalArticle',
        'title': article.get('title', ''),
        'publicationTitle': article.get('source', 'Unknown'),
        'creators': [],
        'date': article.get('date', ''),
        'dateAdded': datetime.now().isoformat(),
        'tags': [],
        'notes': f"Source: {article.get('source', 'Unknown')}\nProcessed: {article.get('processed_date', '')}",
        'attachments': [],
    }

    # Add author as creator
    author = article.get('author')
    if author:
        # Try to split multiple authors
        authors = [a.strip() for a in author.split(' and ')]
        for auth in authors:
            zotero_entry['creators'].append({
                'creatorType': 'author',
                'name': auth
            })

    # Add keywords as tags
    for keyword in article.get('keywords', []):
        zotero_entry['tags'].append({
            'tag': keyword,
            'type': 1
        })

    return zotero_entry


def export_to_csv(articles: List[Dict], output_path: Path = None) -> None:
    """
    Export articles in Zotero CSV format.

    Args:
        articles: List of article metadata
        output_path: Path to save CSV file
    """
    if not output_path:
        output_path = METADATA_REGISTRY.parent / 'zotero_export.csv'

    if not articles:
        print("No articles to export.")
        return

    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'Title', 'Publication', 'Author', 'Date', 'Keywords',
                'Source', 'Notes'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for article in articles:
                keywords = '; '.join(article.get('keywords', []))
                row = {
                    'Title': article.get('title', ''),
                    'Publication': article.get('source', 'Unknown'),
                    'Author': article.get('author', ''),
                    'Date': article.get('date', ''),
                    'Keywords': keywords,
                    'Source': article.get('source', ''),
                    'Notes': f"Processed: {article.get('processed_date', '')}"
                }
                writer.writerow(row)

        print(f"\n✓ Exported {len(articles)} articles to {output_path}")
        print(f"✓ File is ready for import into Zotero")
        print(f"✓ In Zotero: File → Import → Select the CSV file")

    except IOError as e:
        print(f"✗ Error writing CSV: {e}")


def export_to_json(articles: List[Dict], output_path: Path = None) -> None:
    """
    Export articles in Zotero JSON format.

    Args:
        articles: List of article metadata
        output_path: Path to save JSON file
    """
    if not output_path:
        output_path = METADATA_REGISTRY.parent / 'zotero_export.json'

    if not articles:
        print("No articles to export.")
        return

    try:
        zotero_entries = [format_for_zotero(article) for article in articles]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(zotero_entries, f, indent=2)

        print(f"\n✓ Exported {len(articles)} articles to {output_path}")
        print(f"✓ JSON format with full article metadata")
        print(f"✓ Can be imported into Zotero or other reference managers")

    except IOError as e:
        print(f"✗ Error writing JSON: {e}")


def list_exportable(articles: List[Dict]) -> None:
    """Show articles available for Zotero export."""
    if not articles:
        print("No articles available.")
        return

    print(f"\n{'='*80}")
    print(f"ARTICLES READY FOR ZOTERO EXPORT ({len(articles)} total)")
    print(f"{'='*80}\n")

    for i, article in enumerate(articles, 1):
        print(f"[{i}] {article.get('title', 'Untitled')}")
        print(f"    Author:  {article.get('author', 'Unknown')}")
        print(f"    Source:  {article.get('source', 'Unknown')}")
        print(f"    Date:    {article.get('date', 'Unknown')}")
        print(f"    Keywords: {', '.join(article.get('keywords', []))}")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Export articles to Zotero reference manager"
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List articles available for export'
    )
    parser.add_argument(
        '--export',
        type=str,
        choices=['csv', 'json', 'all'],
        help='Export articles in specified format or both'
    )

    args = parser.parse_args()

    articles = load_articles()

    if args.list:
        list_exportable(articles)
    elif args.export:
        if args.export in ['csv', 'all']:
            export_to_csv(articles)
        if args.export in ['json', 'all']:
            export_to_json(articles)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
