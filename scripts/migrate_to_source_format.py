#!/usr/bin/env python3
"""
Migrate existing markdown files to include source in filename.

Renames markdown files from YYYY-MM-DD_Title.md format to
YYYY-MM-DD_Source_Title.md format based on metadata registry.

Usage:
    python migrate_to_source_format.py              # Migrate all files
    python migrate_to_source_format.py --dry-run    # Preview without changing
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List
import re

from config import METADATA_REGISTRY, OUTPUT_DIR, ARCHIVE_DIR
from utils import parse_metadata_from_filename


def load_metadata() -> Dict:
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


def migrate_files(dry_run: bool = False) -> None:
    """Migrate markdown files to include source in filename."""
    registry = load_metadata()
    articles = registry.get('articles', [])

    if not articles:
        print("No articles in metadata registry.")
        return

    print(f"\n{'=' * 80}")
    print("Markdown File Migration - Adding Source to Filenames")
    if dry_run:
        print("[DRY RUN MODE - No files will be renamed]")
    print(f"{'=' * 80}\n")

    migrated_count = 0
    skipped_count = 0
    error_count = 0
    updated_articles = []

    for article in articles:
        output_file = article.get('output_file', '')
        source = article.get('source')

        # If source not in metadata, try to extract from original PDF filename
        if not source:
            source_pdf = article.get('source_file', '')
            if source_pdf:
                pdf_metadata = parse_metadata_from_filename(source_pdf)
                source = pdf_metadata.get('source', 'Unknown')
            else:
                source = 'Unknown'

        # Check if filename already has source prefix (format: YYYY-MM-DD_Source_Title.md)
        if output_file.count('_') >= 2:
            # Check if it looks like it already has source
            date_part = output_file[:10]  # YYYY-MM-DD
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_part):
                parts = output_file[11:].split('_', 1)  # Skip date and first underscore
                if len(parts) > 0 and parts[0].upper() in ['EBSCO', 'ArticleForge', 'HARVARD', 'UNKNOWN']:
                    # Already has source prefix
                    print(f"✓ Already migrated: {output_file}")
                    updated_articles.append(article)
                    skipped_count += 1
                    continue

        # Build new filename with source
        date_match = re.match(r'^(\d{4}-\d{2}-\d{2})_(.+)\.md$', output_file)
        if date_match:
            date_part = date_match.group(1)
            title_part = date_match.group(2)
            new_filename = f"{date_part}_{source}_{title_part}.md"
        else:
            # No date prefix, just add source
            new_filename = f"{source}_{output_file}"

        # Skip if filename would be the same
        if new_filename == output_file:
            print(f"✓ No change needed: {output_file}")
            updated_articles.append(article)
            skipped_count += 1
            continue

        source_path = OUTPUT_DIR / output_file
        dest_path = OUTPUT_DIR / new_filename

        # Check if source file exists
        if not source_path.exists():
            print(f"✗ File not found: {output_file}")
            error_count += 1
            continue

        # Check if destination already exists
        if dest_path.exists():
            print(f"⚠️  Skipping: {new_filename} already exists")
            skipped_count += 1
            continue

        # Perform migration
        if dry_run:
            print(f"[DRY RUN] Would rename:")
            print(f"  From: {output_file}")
            print(f"  To:   {new_filename}\n")
            migrated_count += 1
        else:
            try:
                source_path.rename(dest_path)
                print(f"✓ Migrated: {new_filename}")
                migrated_count += 1
            except Exception as e:
                print(f"✗ Error migrating {output_file}: {e}")
                error_count += 1
                continue

        # Update article metadata with new filename
        article['output_file'] = new_filename
        updated_articles.append(article)

    # Update registry if not dry run
    if not dry_run and migrated_count > 0:
        registry['articles'] = updated_articles
        registry['last_updated'] = json.dumps({
            'timestamp': str(Path.cwd()),
            'migration': 'source_format_v1'
        })
        try:
            with open(METADATA_REGISTRY, 'w') as f:
                json.dump(registry, f, indent=2)
            print(f"\n✓ Metadata registry updated")
        except IOError as e:
            print(f"\n✗ Error updating registry: {e}")

    # Print summary
    print(f"\n{'=' * 80}")
    print("MIGRATION SUMMARY")
    print(f"{'=' * 80}")
    print(f"Migrated:  {migrated_count}")
    print(f"Skipped:   {skipped_count}")
    print(f"Errors:    {error_count}")
    print(f"Total:     {migrated_count + skipped_count + error_count}")
    print(f"{'=' * 80}\n")

    if migrated_count > 0 and not dry_run:
        print(f"✓ Migration complete!")
        print(f"✓ Output folder: {OUTPUT_DIR}")
        print(f"✓ Metadata registry updated: {METADATA_REGISTRY}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate markdown files to include source in filename"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview migration without making changes'
    )

    args = parser.parse_args()
    migrate_files(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
