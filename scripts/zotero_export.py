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
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from config import METADATA_REGISTRY, ARCHIVE_DIR


# ---------------------------------------------------------------------------
# Task 3.3 — Backward-compat shim
# ---------------------------------------------------------------------------

def _normalize_record(article: Dict) -> Dict:
    """
    Normalize an article record to v2 schema shape regardless of schema_version.

    For legacy (v1) records that lack structured fields, synthesizes them from
    the flat legacy fields so that all exporters can use a single code path.

    Args:
        article: Raw article dict from metadata registry

    Returns:
        Normalized dict with guaranteed presence of v2 keys
        (values may be None/empty if data is not available)
    """
    record = dict(article)  # shallow copy — don't mutate original

    # --- authors (List[Dict]) ---
    if not record.get('authors'):
        raw_author = record.get('author', '') or ''
        if raw_author:
            # Synthesize minimal structured authors from legacy string
            authors = []
            for segment in re.split(r'\s*;\s*|\s+and\s+', raw_author, flags=re.IGNORECASE):
                segment = segment.strip()
                if not segment:
                    continue
                parts = segment.split()
                if len(parts) >= 2:
                    first = ' '.join(parts[:-1])
                    last = parts[-1]
                else:
                    first = ''
                    last = segment
                authors.append({'first': first, 'last': last, 'full': segment, 'affiliation': None})
            record['authors'] = authors
        else:
            record['authors'] = []

    # --- publication (Dict) ---
    if not record.get('publication'):
        record['publication'] = {'journal': record.get('source'), 'volume': None, 'issue': None, 'pages': None}

    # --- doi ---
    record.setdefault('doi', None)

    # --- url ---
    record.setdefault('url', None)

    # --- abstract ---
    record.setdefault('abstract', None)

    # --- pdf_archive_path ---
    if not record.get('pdf_archive_path'):
        source_file = record.get('source_file', '')
        if source_file:
            candidate = ARCHIVE_DIR / source_file
            record['pdf_archive_path'] = str(candidate) if candidate.exists() else None
        else:
            record['pdf_archive_path'] = None

    return record


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
    Format article metadata for Zotero JSON import.

    Normalizes v1/v2 records via _normalize_record() and produces a
    Zotero-compatible entry with all relevant fields including DOI, URL,
    volume/issue/pages, abstract, and PDF attachment link.

    Args:
        article: Article metadata from registry (v1 or v2 schema)

    Returns:
        Zotero-formatted dictionary
    """
    rec = _normalize_record(article)
    pub = rec.get('publication') or {}

    zotero_entry = {
        'itemType': 'journalArticle',
        'title': rec.get('title', ''),
        'publicationTitle': pub.get('journal') or rec.get('source', 'Unknown'),
        'creators': [],
        'date': rec.get('date', ''),
        'DOI': rec.get('doi', ''),
        'url': rec.get('url', ''),
        'volume': pub.get('volume', ''),
        'issue': pub.get('issue', ''),
        'pages': pub.get('pages', ''),
        'abstractNote': rec.get('abstract', ''),
        'dateAdded': datetime.now().isoformat(),
        'tags': [],
        'notes': f"Source: {rec.get('source', 'Unknown')}\nProcessed: {rec.get('processed_date', '')}",
        'attachments': [],
    }

    # Task 3.2 — Authors: use structured list (first/last) when available
    for author in rec.get('authors', []):
        creator = {'creatorType': 'author'}
        if author.get('first') or author.get('last'):
            creator['firstName'] = author.get('first', '')
            creator['lastName'] = author.get('last', '')
        else:
            creator['name'] = author.get('full', '')
        zotero_entry['creators'].append(creator)

    # Add keywords as tags
    for keyword in rec.get('keywords', []):
        zotero_entry['tags'].append({
            'tag': keyword,
            'type': 1
        })

    # Task 3.1 — PDF attachment linking
    pdf_path = rec.get('pdf_archive_path')
    if pdf_path:
        zotero_entry['attachments'].append({
            'title': 'PDF',
            'mimeType': 'application/pdf',
            'path': pdf_path,
        })

    return zotero_entry


def export_to_csv(articles: List[Dict], output_path: Path = None) -> None:
    """
    Export articles in Zotero CSV format.

    Includes v2 fields: DOI, URL, Volume, Issue, Pages, Abstract,
    File Attachments (for Zotero linked-file import).

    Args:
        articles: List of article metadata (v1 or v2 schema)
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
                'DOI', 'URL', 'Volume', 'Issue', 'Pages', 'Abstract',
                'File Attachments', 'Source', 'Notes'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for article in articles:
                rec = _normalize_record(article)
                pub = rec.get('publication') or {}
                keywords = '; '.join(rec.get('keywords', []))

                # Author string from structured list or legacy field
                authors_list = rec.get('authors', [])
                if authors_list:
                    author_str = '; '.join(
                        f"{a.get('last', '')}, {a.get('first', '')}".strip(', ')
                        for a in authors_list if a.get('last') or a.get('first') or a.get('full')
                    )
                else:
                    author_str = rec.get('author', '')

                row = {
                    'Title': rec.get('title', ''),
                    'Publication': pub.get('journal') or rec.get('source', 'Unknown'),
                    'Author': author_str,
                    'Date': rec.get('date', ''),
                    'Keywords': keywords,
                    'DOI': rec.get('doi', '') or '',
                    'URL': rec.get('url', '') or '',
                    'Volume': pub.get('volume', '') or '',
                    'Issue': pub.get('issue', '') or '',
                    'Pages': pub.get('pages', '') or '',
                    'Abstract': rec.get('abstract', '') or '',
                    'File Attachments': rec.get('pdf_archive_path', '') or '',
                    'Source': rec.get('source', ''),
                    'Notes': f"Processed: {rec.get('processed_date', '')}"
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

    Uses format_for_zotero() which normalizes v1/v2 records and includes
    structured creators (firstName/lastName), DOI, URL, abstract, and
    PDF attachment links.

    Args:
        articles: List of article metadata (v1 or v2 schema)
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
            json.dump(zotero_entries, f, indent=2, ensure_ascii=False)

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

    v2 additions: doi, url, volume, number (issue), pages, abstract,
    authors in "Last, First and Last, First" format, file attachment.

    Args:
        articles: List of article metadata (v1 or v2 schema)
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
            rec = _normalize_record(article)
            pub = rec.get('publication') or {}

            # Create citation key
            cite_key = sanitize_bibtex_key(rec)

            # Parse date
            date = rec.get('date', '') or ''
            year = ''
            month = ''
            day = ''

            if date:
                parts = date.split('-')
                if len(parts) >= 1:
                    year = parts[0]
                if len(parts) >= 2:
                    month_map = ['', 'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                    month_num = int(parts[1]) if parts[1].isdigit() else 0
                    month = month_map[month_num] if 0 < month_num < len(month_map) else ''
                if len(parts) >= 3:
                    day = parts[2]

            # Authors: "Last, First and Last, First" format (BibTeX convention)
            authors_list = rec.get('authors', [])
            if authors_list:
                author_parts = []
                for a in authors_list:
                    if a.get('last') and a.get('first'):
                        author_parts.append(f"{a['last']}, {a['first']}")
                    elif a.get('last'):
                        author_parts.append(a['last'])
                    elif a.get('full'):
                        author_parts.append(a['full'])
                author_str = ' and '.join(author_parts) if author_parts else 'Unknown'
            else:
                author_str = rec.get('author', '') or 'Unknown'

            # Journal: prefer structured publication.journal, fall back to source
            journal = pub.get('journal') or rec.get('source', 'Unknown')

            # Build BibTeX entry
            entry = f"@article{{{cite_key},\n"
            entry += f'  title = {{{rec.get("title", "Unknown")}}},\n'
            entry += f'  author = {{{author_str}}},\n'
            entry += f'  journal = {{{journal}}},\n'

            if year:
                entry += f'  year = {{{year}}},\n'
            if month:
                entry += f'  month = {month},\n'
            if day:
                entry += f'  day = {{{day}}},\n'

            # v2 publication detail fields
            if pub.get('volume'):
                entry += f'  volume = {{{pub["volume"]}}},\n'
            if pub.get('issue'):
                entry += f'  number = {{{pub["issue"]}}},\n'
            if pub.get('pages'):
                entry += f'  pages = {{{pub["pages"]}}},\n'

            # DOI and URL
            if rec.get('doi'):
                entry += f'  doi = {{{rec["doi"]}}},\n'
            if rec.get('url'):
                entry += f'  url = {{{rec["url"]}}},\n'

            # Abstract (BibTeX abstract field)
            if rec.get('abstract'):
                # Escape braces in abstract text for BibTeX safety
                abstract_safe = rec['abstract'].replace('{', r'\{').replace('}', r'\}')
                entry += f'  abstract = {{{abstract_safe}}},\n'

            # Keywords
            keywords = rec.get('keywords', [])
            if keywords:
                entry += f'  keywords = {{{", ".join(keywords)}}},\n'

            # PDF file attachment (Zotero linked file format)
            pdf_path = rec.get('pdf_archive_path')
            if pdf_path:
                entry += f'  file = {{:{pdf_path}:PDF}},\n'

            # Markdown output reference as note
            output_file = rec.get('output_file', '')
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
