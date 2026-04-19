#!/usr/bin/env python3
"""
ArticleForge Article Processing Pipeline

Converts PDF articles to Markdown with metadata extraction and keyword tagging.
Maintains centralized JSON metadata registry.

Usage:
    python process_articles.py                 # Process all files in intake/
    python process_articles.py --rebuild       # Rebuild metadata registry from scratch
    python process_articles.py --dry-run       # Preview without writing files
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Import local modules
from config import (
    INTAKE_DIR, OUTPUT_DIR, ARCHIVE_DIR, METADATA_DIR,
    METADATA_REGISTRY, MIN_KEYWORDS, MAX_KEYWORDS
)
from utils import (
    extract_text_from_pdf, extract_pdf_metadata, extract_title, extract_author, extract_date,
    extract_keywords, sanitize_filename, create_markdown_content,
    parse_metadata_from_filename, extract_publication,
    extract_doi, extract_authors, extract_publication_details, extract_abstract,
)
from metadata_enricher import enrich as enrich_metadata


class ArticleProcessor:
    """Main processor for converting PDFs to Markdown articles."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.metadata = self.load_metadata_registry()
        self.manual_overrides = self.load_manual_overrides()
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
        }

    def load_metadata_registry(self) -> Dict:
        """Load existing metadata registry or create new one."""
        if METADATA_REGISTRY.exists():
            try:
                with open(METADATA_REGISTRY, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load metadata registry: {e}")
                return {"articles": [], "last_updated": None}
        else:
            return {"articles": [], "last_updated": None}

    def load_manual_overrides(self) -> Dict:
        """Load manual metadata overrides for problem PDFs."""
        overrides_file = METADATA_DIR / "manual_metadata_overrides.json"
        if overrides_file.exists():
            try:
                with open(overrides_file, 'r') as f:
                    data = json.load(f)
                    # Convert to dict keyed by source_file for easy lookup
                    return {item['source_file']: item for item in data.get('overrides', [])}
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load manual overrides: {e}")
                return {}
        return {}

    def save_metadata_registry(self):
        """Save metadata registry to JSON."""
        if not self.dry_run:
            self.metadata['last_updated'] = datetime.now().isoformat()
            try:
                with open(METADATA_REGISTRY, 'w') as f:
                    json.dump(self.metadata, f, indent=2)
                print(f"\n✓ Metadata registry saved to {METADATA_REGISTRY}")
            except IOError as e:
                print(f"✗ Error saving metadata registry: {e}")

    def article_exists(self, pdf_filename: str) -> bool:
        """Check if article has already been processed."""
        for article in self.metadata.get('articles', []):
            if article.get('source_file') == pdf_filename:
                return True
        return False

    def process_pdf(self, pdf_path: Path) -> Optional[Dict]:
        """
        Process a single PDF file and return metadata.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with article metadata or None if processing failed
        """
        print(f"\nProcessing: {pdf_path.name}")

        try:
            # Extract PDF metadata first (from document properties)
            print("  → Extracting PDF metadata...")
            pdf_metadata = extract_pdf_metadata(pdf_path)

            # Extract text from PDF
            print("  → Extracting text...")
            text = extract_text_from_pdf(pdf_path)

            if not text or len(text) < 100:
                print("  ✗ No text extracted from PDF (may be empty/corrupted)")
                return None

            # Extract metadata (uses PDF metadata as primary source, falls back to text parsing)
            print("  → Parsing title, author, date...")
            title = extract_title(text, pdf_metadata.get('title'))
            author = extract_author(text, pdf_metadata.get('author'))
            date = extract_date(text, pdf_metadata.get('date'))

            if not title:
                # Check for manual override
                override = self.manual_overrides.get(pdf_path.name)
                if override:
                    print("  → Using manual metadata override...")
                    title = override.get('title')
                    author = override.get('author') or author
                    date = override.get('date') or date
                    print(f"  ✓ Loaded from override: {title}")
                else:
                    print("  ✗ Could not extract article title")
                    return None

            # Extract keywords
            keywords = extract_keywords(text, num_keywords=min(MAX_KEYWORDS, max(MIN_KEYWORDS, 5)))

            # Extract filename metadata first
            filename_metadata = parse_metadata_from_filename(pdf_path.name)

            # Extract source: try publication name from text first, then filename
            publication = extract_publication(text)
            if publication:
                source = publication
            else:
                source = filename_metadata.get('source', 'Unknown')

            # --- Phase 1 / 2 new extractions ---
            print("  → Extracting DOI, structured authors, publication details...")
            doi = extract_doi(text, pdf_metadata)
            authors_structured = extract_authors(text, pdf_metadata.get('author'))
            pub_details = extract_publication_details(text)
            abstract = extract_abstract(text)
            # PDF archive path (will be set after archiving)
            pdf_archive_path = str(ARCHIVE_DIR / pdf_path.name)

            # Sanitize title for filename
            safe_title = sanitize_filename(title)
            if date:
                filename = f"{date}_{source}_{safe_title}.md"
            else:
                filename = f"{source}_{safe_title}.md"

            # Create markdown content
            md_content = create_markdown_content(
                title=title,
                author=author,
                date=date,
                keywords=keywords,
                text=text,
                source=source
            )

            # Prepare metadata entry (v2 schema)
            metadata_entry = {
                # --- legacy fields (v1 compat) ---
                'source_file': pdf_path.name,
                'output_file': filename,
                'title': title,
                'author': author,
                'date': date,
                'keywords': keywords,
                'text_length': len(text),
                'processed_date': datetime.now().isoformat(),
                'pdf_metadata': {
                    'title_source': 'PDF' if pdf_metadata.get('title') else 'text_parsed',
                    'author_source': 'PDF' if pdf_metadata.get('author') else 'text_parsed',
                    'date_source': 'PDF' if pdf_metadata.get('date') else 'text_parsed',
                },
                # --- v2 fields ---
                'schema_version': 2,
                'authors': authors_structured,
                'doi': doi,
                'url': None,
                'abstract': abstract,
                'publication': pub_details,
                'pdf_archive_path': pdf_archive_path,
                'extraction_confidence': {},
                'extraction_sources': {},
            }

            # Seed confidence for locally-extracted fields
            if doi:
                metadata_entry['extraction_confidence']['doi'] = 0.9
                metadata_entry['extraction_sources']['doi'] = 'text_regex'
            if authors_structured:
                metadata_entry['extraction_confidence']['authors'] = (
                    0.9 if pdf_metadata.get('author') else 0.6
                )
                metadata_entry['extraction_sources']['authors'] = (
                    'pdf_metadata' if pdf_metadata.get('author') else 'text_parsed'
                )

            # Add filename-derived metadata
            metadata_entry.update(filename_metadata)

            # --- Phase 2: Semantic enrichment via CrossRef ---
            print("  → Enriching via CrossRef...")
            metadata_entry = enrich_metadata(metadata_entry, text)

            # Write markdown file
            if not self.dry_run:
                output_path = OUTPUT_DIR / filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                print(f"  ✓ Wrote: {output_path.name}")

                # Move PDF to archive
                archive_path = ARCHIVE_DIR / pdf_path.name
                pdf_path.rename(archive_path)
                print(f"  ✓ Archived: {archive_path.name}")

                # Add to metadata registry
                self.metadata['articles'].append(metadata_entry)

            else:
                print(f"  [DRY RUN] Would write: {filename}")
                print(f"  [DRY RUN] Would archive PDF and update registry")

            return metadata_entry

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def process_all(self) -> None:
        """Process all PDFs in intake directory."""
        intake_files = list(INTAKE_DIR.glob('*.pdf'))

        if not intake_files:
            print("No PDF files found in intake/ directory.")
            return

        print(f"\n{'=' * 70}")
        print(f"ArticleForge Article Processing Pipeline")
        print(f"Found {len(intake_files)} PDF(s) to process")
        if self.dry_run:
            print("[DRY RUN MODE - No files will be written]")
        print(f"{'=' * 70}")

        for pdf_path in sorted(intake_files):
            self.stats['total_processed'] += 1

            # Check if already processed
            if self.article_exists(pdf_path.name):
                print(f"\nSkipping: {pdf_path.name} (already processed)")
                self.stats['skipped'] += 1
                continue

            # Process PDF
            result = self.process_pdf(pdf_path)
            if result:
                self.stats['successful'] += 1
            else:
                self.stats['failed'] += 1

        # Print summary
        self.print_summary()

        # Save metadata registry
        if self.stats['successful'] > 0 or self.stats['failed'] > 0:
            self.save_metadata_registry()

    def print_summary(self) -> None:
        """Print processing summary."""
        print(f"\n{'=' * 70}")
        print("PROCESSING SUMMARY")
        print(f"{'=' * 70}")
        print(f"Total processed:  {self.stats['total_processed']}")
        print(f"Successful:       {self.stats['successful']}")
        print(f"Failed:           {self.stats['failed']}")
        print(f"Skipped:          {self.stats['skipped']}")
        print(f"{'=' * 70}")

        if self.stats['successful'] > 0:
            print(f"\n✓ Output files: {OUTPUT_DIR}")
            print(f"✓ Archived PDFs: {ARCHIVE_DIR}")
            print(f"✓ Metadata registry: {METADATA_REGISTRY}")

    def rebuild_registry(self) -> None:
        """Rebuild metadata registry from existing output files."""
        print(f"\nRebuilding metadata registry from {OUTPUT_DIR}")

        self.metadata = {"articles": [], "last_updated": None}

        md_files = list(OUTPUT_DIR.glob('*.md'))
        if not md_files:
            print("No markdown files found in output/ directory.")
            return

        for md_path in sorted(md_files):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse YAML frontmatter
                if content.startswith('---'):
                    _, frontmatter, _ = content.split('---', 2)
                    entry = {'output_file': md_path.name}

                    # Extract fields from YAML
                    for line in frontmatter.strip().split('\n'):
                        if ': ' in line:
                            key, value = line.split(': ', 1)
                            key = key.strip()

                            # Parse keywords array
                            if key == 'keywords':
                                value = value.strip('[]').split(', ')

                            entry[key] = value

                    self.metadata['articles'].append(entry)
                    print(f"  ✓ {md_path.name}")

            except Exception as e:
                print(f"  ✗ Error reading {md_path.name}: {e}")

        self.save_metadata_registry()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process ArticleForge articles from PDF to Markdown"
    )
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Rebuild metadata registry from existing output files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview processing without writing files'
    )

    args = parser.parse_args()

    processor = ArticleProcessor(dry_run=args.dry_run)

    if args.rebuild:
        processor.rebuild_registry()
    else:
        processor.process_all()


if __name__ == '__main__':
    main()
