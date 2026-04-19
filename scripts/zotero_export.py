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


def sanitize_bibtex_key(article: Dict) -> str:
    """
    Create a valid BibTeX citation key from article title and date.

    BibTeX keys must be alphanumeric with hyphens/underscores.
    Format: YYYY_FirstWords_of_Title
    """
    date = article.get('date', '2000')
    year = date.split('-')[0] if date else '2000'

    title = article.get('title', 'Unknown')
    # Take first 3 words, lowercase, remove non-alphanumeric
    words = title.split()[:3]
    title_part = '_'.join(w.lower() for w in words if w.isalnum())

    # Clean up: remove special characters, keep only alphanumeric and underscore
    title_part = ''.join(c if c.isalnum() or c == '_' else '' for c in title_part)

    return f"{year}_{title_part}"[:50]  # Keep it reasonable length


def export_to_bibtex(articles: List[Dict], output_path: Path = None) -> None:
    """
    Export articles in BibTeX format (native Zotero import).

    BibTeX is ideal for Zotero because it's a standard citation format
    that Zotero can parse directly without data loss.

    Args:
        articles: List of article metadata
        output_path: Path to save BibTeX file
    """
    if not output_path:
        output_path = METADATA_REGISTRY.parent / 'zotero_export.bib'

    if not articles:
        print("No articles to export.")
        return

    try:
        bibtex_entries = []

        for article in articles:
            # Create citation key
            cite_key = sanitize_bibtex_key(article)

            # Parse date
            date = article.get('date', '')
            year = ''
            month = ''
            day = ''

            if date:
                parts = date.split('-')
                if len(parts) >= 1:
                    year = parts[0]
                if len(parts) >= 2:
                    # Convert month number to BibTeX month abbreviation
                    month_map = ['', 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                    month_num = int(parts[1]) if parts[1].isdigit() else 0
                    month = month_map[month_num] if 0 < month_num < len(month_map) else ''
                if len(parts) >= 3:
                    day = parts[2]

            # Format author(s) for BibTeX (Last, First and Last, First)
            author = article.get('author', '')
            if not author:
                author = 'Unknown'

            # Build BibTeX entry
            entry = f"@article{{{cite_key},\n"
            entry += f'  title = {{{article.get("title", "Unknown")}}},\n'

            # Add author
            entry += f'  author = {{{author}}},\n'

            # Add publication (journal/source)
            source = article.get('source', 'Unknown')
            entry += f'  journal = {{{source}}},\n'

            # Add date components
            if year:
                entry += f'  year = {{{year}}},\n'
            if month:
                entry += f'  month = {month},\n'
            if day:
                entry += f'  day = {{{day}}},\n'

            # Add keywords as note
            keywords = article.get('keywords', [])
            if keywords:
                keywords_str = ', '.join(keywords)
                entry += f'  keywords = {{{keywords_str}}},\n'

            # Add URL or file reference if available
            output_file = article.get('output_file', '')
            if output_file:
                entry += f'  note = {{Markdown: {output_file}}},\n'

            # Close entry
            entry = entry.rstrip(',\n') + '\n}\n'
            bibtex_entries.append(entry)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(bibtex_entries))

        print(f"\n✓ Exported {len(articles)} articles to {output_path}")
        print(f"✓ BibTeX format (native Zotero import)")
        print(f"✓ In Zotero: File → Import → Select the .bib file")
        print(f"✓ BibTeX is ideal because Zotero parses it without data loss")

    except IOError as e:
        print(f"✗ Error writing BibTeX: {e}")


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
        choices=['csv', 'json', 'bibtex', 'all'],
        help='Export articles in specified format (bibtex recommended for Zotero)'
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
        if args.export in ['bibtex', 'all']:
            export_to_bibtex(articles)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
