#!/usr/bin/env python3
"""
Rename archived PDFs to match their markdown filenames.

This script reads the metadata registry and renames PDFs from their original
EBSCO filenames (e.g., EBSCO-FullText-04_18_2026 (1).pdf) to match the
processed markdown filenames (e.g., 2024-07-16_Article_Title.pdf).

Usage:
    python rename_archived_pdfs.py              # Rename all PDFs
    python rename_archived_pdfs.py --dry-run    # Preview without renaming
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List

from config import METADATA_REGISTRY, ARCHIVE_DIR


def load_metadata() -> List[Dict]:
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


def rename_pdfs(dry_run: bool = False) -> None:
    """Rename PDFs in archive to match markdown filenames."""
    articles = load_metadata()

    if not articles:
        print("No articles found in metadata registry.")
        return

    print(f"\n{'=' * 80}")
    print(f"PDF Renaming Utility")
    if dry_run:
        print("[DRY RUN MODE - No files will be renamed]")
    print(f"{'=' * 80}\n")

    renamed_count = 0
    skipped_count = 0
    error_count = 0

    for article in articles:
        source_file = article.get('source_file')
        output_file = article.get('output_file')

        if not source_file or not output_file:
            print(f"⚠️  Skipping: Missing source or output file info")
            skipped_count += 1
            continue

        # Convert markdown filename to PDF filename
        pdf_filename = output_file.replace('.md', '.pdf')

        # Source and destination paths
        source_path = ARCHIVE_DIR / source_file
        dest_path = ARCHIVE_DIR / pdf_filename

        # Check if source exists
        if not source_path.exists():
            print(f"✗ Not found: {source_file}")
            error_count += 1
            continue

        # Skip if already renamed
        if source_path == dest_path:
            print(f"✓ Already named: {pdf_filename}")
            skipped_count += 1
            continue

        # Skip if destination already exists (avoid overwrites)
        if dest_path.exists():
            print(f"⚠️  Skipping: {pdf_filename} already exists")
            skipped_count += 1
            continue

        # Perform rename
        if dry_run:
            print(f"[DRY RUN] Would rename:")
            print(f"  From: {source_file}")
            print(f"  To:   {pdf_filename}\n")
        else:
            try:
                source_path.rename(dest_path)
                print(f"✓ Renamed: {pdf_filename}")
                renamed_count += 1
            except Exception as e:
                print(f"✗ Error renaming {source_file}: {e}")
                error_count += 1

    # Print summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Renamed:  {renamed_count}")
    print(f"Skipped:  {skipped_count}")
    print(f"Errors:   {error_count}")
    print(f"Total:    {renamed_count + skipped_count + error_count}")
    print(f"{'=' * 80}\n")

    if renamed_count > 0 and not dry_run:
        print(f"✓ PDFs renamed successfully!")
        print(f"✓ Archive folder: {ARCHIVE_DIR}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Rename archived PDFs to match markdown filenames"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview renaming without making changes'
    )

    args = parser.parse_args()
    rename_pdfs(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
