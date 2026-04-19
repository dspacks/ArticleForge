# Source Tracking Guide

## Overview

The ArticleForge processing system now includes the source database/journal in markdown filenames, making it easy to identify where each article came from at a glance.

## Filename Format

**New format:** `YYYY-MM-DD_SOURCE_Title.md`

Example: `2026-02-10_EBSCO_Why_the_Digital_Product_Model.md`

- **YYYY-MM-DD** — Publication date
- **SOURCE** — Database/journal source (e.g., EBSCO, ArticleForge, Harvard)
- **Title** — Article title (sanitized for filesystem)

## How It Works

### Processing New Articles

When you process new PDFs, the system automatically extracts the source from the PDF filename and includes it in the output markdown filename.

**EBSCO exports example:**
- Input PDF: `EBSCO-FullText-04_18_2026 (27).pdf`
- Output MD: `2026-02-10_EBSCO_Why_the_Digital_Product_Model.md`
- Source detected: `EBSCO`

### Metadata Storage

The source is also stored in the metadata registry (`metadata/articles_metadata.json`) for each article:

```json
{
  "source": "EBSCO",
  "output_file": "2026-02-10_EBSCO_Why_the_Digital_Product_Model.md",
  "title": "Why the Digital Product Model Beats Project-Based Approaches",
  "author": "Ryan Nelson and Thomas H. Davenport",
  ...
}
```

### Querying by Source

The `query_metadata.py` script now displays source information:

```bash
# List all articles (shows source for each)
python scripts/query_metadata.py --list

# Export to CSV (includes source column)
python scripts/query_metadata.py --export csv

# View statistics (shows breakdown by source)
python scripts/query_metadata.py --stats
```

## Migrating Existing Files

If you want to update your existing markdown files to include source prefixes:

```bash
# Preview changes without making them
python scripts/migrate_to_source_format.py --dry-run

# Actually perform the migration
python scripts/migrate_to_source_format.py
```

This script will:
1. Read the metadata registry to get source information for each article
2. Rename markdown files from `YYYY-MM-DD_Title.md` to `YYYY-MM-DD_SOURCE_Title.md`
3. Update the metadata registry with new filenames
4. Skip files that are already in the new format

## Source Detection

The system currently detects these sources from filename patterns:

- **EBSCO** — EBSCO database exports (`EBSCO-FullText-*.pdf`)
- **Custom sources** — Add support for other sources by extending `parse_metadata_from_filename()` in `utils.py`

To add a new source type:

1. Edit `scripts/utils.py`
2. Update the `parse_metadata_from_filename()` function to detect your pattern
3. Return `{'source': 'YourSource', ...}` in the metadata dictionary

Example:
```python
# Detect custom format: ArticleForge-YYYY-MM-DD-*.pdf
match = re.match(r'ArticleForge-(\d{4})-(\d{2})-(\d{2})', pdf_filename)
if match:
    metadata['source'] = 'ArticleForge'
```

## Integration Points

- **process_articles.py** — Extracts source and includes in output filename
- **query_metadata.py** — Displays source in listings and exports
- **rename_archived_pdfs.py** — PDFs are renamed to match markdown (with source)
- **hbr.py** — CLI shows source in article details

## FAQ

**Q: Will my existing files be renamed automatically?**
A: No, use `migrate_to_source_format.py` to rename them. This gives you control over when the change happens.

**Q: Can I specify a different source for an article?**
A: Yes, edit the metadata registry directly or use `manual_metadata_overrides.json` for the source PDF, then run the migration script.

**Q: What if my PDF filename doesn't match any known source pattern?**
A: The source will default to "Unknown". Extend the source detection logic in `utils.py` to recognize your pattern.

**Q: Does this affect PDF archiving?**
A: Yes, PDFs in the archive are renamed to match their markdown files, so they'll also include the source prefix when you run `rename_archived_pdfs.py`.
