# ArticleForge

A professional-grade Python system for extracting, organizing, and managing academic articles from PDF exports. Works with articles from any publication: Harvard Business Review, WSJ, Forbes, and more.

## 🌟 Features

**Core Capabilities**
- 📥 **PDF Processing**: Extract metadata and text from article PDFs with smart layout handling
- 📊 **Intelligent Extraction**: Title, author, date, and keyword extraction with fallbacks
- 🏷️ **Publication Detection**: Automatically identifies ArticleForge, WSJ, Forbes, McKinsey, Bain, FT
- 📝 **Markdown Conversion**: Creates beautifully formatted markdown with YAML frontmatter
- 🔍 **Full-Text Search**: Search articles by keyword, author, date, or publication source
- 📤 **Multi-Format Export**: BibTeX (recommended), CSV, JSON, and Zotero-compatible formats
- 🔗 **Zotero Integration**: Push articles directly to your Zotero library with full metadata
- 🎨 **Interactive CLI**: Beautiful terminal interface with color-coded output
- 🔧 **Manual Overrides**: Handle problem PDFs with manual metadata entry
- 📊 **Statistics Dashboard**: Real-time system statistics and keyword analysis

## 🏗️ System Architecture

```
article-forge/
├── processing_ui.py              # Interactive CLI interface (main entry point)
├── scripts/
│   ├── config.py                # Configuration and constants
│   ├── utils.py                 # Text extraction & processing utilities
│   ├── process_articles.py      # PDF processing pipeline (core engine)
│   ├── query_metadata.py        # Search and CSV/JSON export
│   ├── zotero_export.py         # Zotero library integration
│   ├── rename_archived_pdfs.py  # Batch PDF renaming utility
│   ├── backfill_source_metadata.py  # Metadata backfilling tool
│   └── migrate_to_source_format.py  # Format migration utility
├── intake/                       # Folder: PDFs waiting to be processed
├── output/                       # Folder: Processed markdown articles
├── pdf_archive/                  # Folder: Original PDFs (archived post-processing)
├── metadata/
│   ├── articles_metadata.json    # Master registry of all articles
│   └── manual_metadata_overrides.json  # Manual metadata for problem PDFs
├── start.sh                      # Quick launcher script
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🚀 Quick Start

### Installation

```bash
# 1. Ensure Python 3.8+ is installed
python3 --version

# 2. Install dependencies
pip install -r requirements.txt

# 3. Place PDFs in the intake/ folder
cp your_articles.pdf intake/

# 4. Launch the system
./start.sh
# OR: python3 processing_ui.py
```

### First Run

1. **Dashboard** shows current system status
2. **Select option 1** to process articles
3. Choose full processing or dry-run preview
4. Articles automatically organized into `output/` folder
5. Original PDFs archived in `pdf_archive/`

## 📋 Menu Options

```
MAIN MENU (interactive CLI):

1. Process Articles       Extract & organize PDFs from intake/
2. Search Articles       Find articles by keyword or author  
3. View Statistics       Show metadata and keyword analysis
4. Export Data           Export to CSV or JSON formats
5. Export to Zotero      Push articles to Zotero library
6. Manage Overrides      Add/edit problem article metadata
7. Rename PDFs           Rename archived PDFs to match markdown
8. List All Articles     Show all processed articles with details
9. Quick Preview         Sample text from any article
0. Settings              View system configuration
! Exit                   Quit the program
```

## 📁 File Organization

### Filename Format

All processed articles follow a consistent naming convention:
```
YYYY-MM-DD_SOURCE_Title.md

Examples:
2026-02-10_HBR_Why_the_Digital_Product_Model.md
2025-12-09_WSJ_In_a_survey_of_1527_adults.md  
2026-02-10_Forbes_AI_Lets_Startups_Grow_Quickly.md
```

**Components**:
- `YYYY-MM-DD` — Publication date (extracted from article metadata)
- `SOURCE` — Publication source (ArticleForge, WSJ, Forbes, EBSCO, Unknown, etc.)
- `Title` — Article title (sanitized for filesystem)

### Folder Structure

```
intake/              → Place PDFs here before processing
output/              → Processed markdown articles
pdf_archive/         → Original PDFs (archived after extraction)
metadata/
  ├── articles_metadata.json      → Master registry (auto-generated)
  └── manual_metadata_overrides.json → Manual fixes for problem PDFs
```

## 🔄 Processing Pipeline

### Stage 1: PDF Discovery
- Scans `intake/` folder for PDF files
- Checks if already processed (avoids duplicates)
- Reports summary: X PDFs found

### Stage 2: Metadata Extraction
- Extracts from PDF document properties (primary)
- Falls back to text parsing if PDF metadata absent
- Handles encoding issues and missing data

### Stage 3: Text Extraction
- **Layout-aware extraction** preserves multi-column structure
- **Automatic text cleaning** fixes merged words (e.g., "areideaWatch" → "are ideaWatch")
- **Table detection** identifies and separates sidebar/table content
- **OCR fallback** for scanned PDFs (if pytesseract installed)

### Stage 4: Publication Detection
- Searches text for publication markers: "Harvard Business Review", "Forbes", etc.
- Extracts source as `ArticleForge`, `WSJ`, `Forbes`, etc.
- Falls back to filename detection (EBSCO, etc.)
- Sets to `Unknown` if no publication found

### Stage 5: Keyword Extraction
- TF-IDF-style analysis with stopword filtering
- Extracts 3-8 relevant keywords per article
- Useful for tagging and full-text search

### Stage 6: Markdown Creation
- Generates YAML frontmatter with metadata
- Appends full article text
- Stores with filename pattern: `YYYY-MM-DD_SOURCE_Title.md`

### Stage 7: Organization & Archival
- Saves markdown to `output/` folder
- Archives original PDF in `pdf_archive/`
- Updates metadata registry with entry for new article

## 🔗 Zotero Integration

### What is Zotero?

[Zotero](https://www.zotero.org/) is a free reference management software for collecting, organizing, and citing research sources.

### Export Articles to Zotero

**⭐ Best Option: BibTeX Format**
BibTeX is a standard citation format that Zotero natively supports with full data preservation.

**Via Interactive CLI** (easiest):
1. Run: `./start.sh`
2. Select option 5: "Export to Zotero"
3. Choose option 1: "BibTeX (⭐ Recommended)"
4. File saved to `metadata/zotero_export.bib`

**Via Command Line**:
```bash
# Export as BibTeX (RECOMMENDED - native Zotero format)
python3 scripts/zotero_export.py --export bibtex

# Export as CSV (Excel-compatible alternative)
python3 scripts/zotero_export.py --export csv

# Export as JSON (full metadata, integrations)
python3 scripts/zotero_export.py --export json

# Export all formats at once
python3 scripts/zotero_export.py --export all

# List articles ready to export
python3 scripts/zotero_export.py --list
```

### Import into Zotero

**For BibTeX (Recommended):**
1. **Open Zotero** application
2. **File** menu → **Import**
3. **Select** the `zotero_export.bib` file
4. **Articles appear** in your library with all metadata preserved:
   - Title, Author, Publication, Date
   - All keywords as tags
   - Processing notes
   - Citation keys for easy reference

**For CSV:**
1. **Open Zotero** application
2. **File** menu → **Import**
3. **Select** the `zotero_export.csv` file
4. Articles are imported with basic metadata

## 🛠️ Configuration

### Edit Processing Settings

Edit `scripts/config.py`:

```python
# Keyword extraction limits
MIN_KEYWORDS = 3      # Minimum keywords per article
MAX_KEYWORDS = 8      # Maximum keywords per article

# Directory paths (customize if needed)
INTAKE_DIR = Path("intake")
OUTPUT_DIR = Path("output")
ARCHIVE_DIR = Path("pdf_archive")
METADATA_DIR = Path("metadata")

# Stopword filtering (words excluded from keywords)
COMMON_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at",
    # ... extensive list included
}
```

### Add New Publications

Edit `scripts/utils.py`, locate `extract_publication()` function:

```python
def extract_publication(text: str) -> Optional[str]:
    publication_markers = {
        'harvard business review': 'ArticleForge',
        'wall street journal': 'WSJ',
        'forbes': 'Forbes',
        # Add your publication here:
        'your publication name': 'YOUR_ABBREV',
    }
    # ... rest of function
```

## 🔧 Troubleshooting

### Articles Not Processing

**Symptom**: "Could not extract article title" errors

**Cause**: PDF text extraction failed or title not found

**Solution**:
1. Check PDF is readable (not corrupted)
2. Use **Option 6: Manage Overrides** in CLI
3. Add manual entry to `metadata/manual_metadata_overrides.json`:

```json
{
  "source_file": "problem_article.pdf",
  "title": "Correct Article Title",
  "author": "Author Name",
  "date": "2026-02-10",
  "notes": "Manual override reason"
}
```

### Text Jumbling/Formatting Issues

**Symptom**: Words appear merged or text out of order

**Cause**: Multi-column PDF layout not properly handled

**Solutions**:
- System automatically uses layout-aware extraction
- Text is cleaned automatically (merged word fixing)
- For extreme cases, try alternative PDF export format
- Manual override allows providing correct text

### Zotero Export Not Working

**Symptom**: "No articles in registry" error

**Cause**: No articles have been processed yet

**Solution**:
1. Process at least one PDF (Option 1 in CLI)
2. Verify metadata file exists: `metadata/articles_metadata.json`
3. Try export again

### Source Detection Showing "Unknown"

**Symptom**: Articles show `Unknown_Title.md` instead of `ArticleForge_Title.md`

**Cause**: Publication name not found in article text

**Solutions**:
1. Check if publication name is in detection list
2. Add publication to `extract_publication()` in `scripts/utils.py`
3. Use manual override to force correct source:

```json
{
  "source_file": "article.pdf",
  "title": "Title",
  "author": "Author",
  "date": "2026-02-10",
  "notes": "Set source to ArticleForge"
}
```

## 💾 Data Formats

### Metadata Registry (JSON)

File: `metadata/articles_metadata.json`

```json
{
  "articles": [
    {
      "source_file": "EBSCO-FullText-04_18_2026 (27).pdf",
      "output_file": "2026-02-10_ArticleForge_Why_Digital_Product_Model.md",
      "title": "Why the Digital Product Model Beats Project-Based Approaches",
      "author": "Ryan Nelson and Thomas H. Davenport",
      "date": "2026-02-10",
      "source": "ArticleForge",
      "keywords": ["product", "project", "digital", "model", "approach"],
      "text_length": 15234,
      "processed_date": "2026-04-19T00:50:30.123456",
      "pdf_metadata": {
        "title_source": "PDF",
        "author_source": "text_parsed",
        "date_source": "PDF"
      },
      "export_date": "2026-04-18"
    }
  ],
  "last_updated": "2026-04-19T00:50:30.123456"
}
```

### Markdown Files

File: `output/2026-02-10_HBR_Article_Title.md`

```markdown
---
title: Article Title
author: Author Name
date: 2026-02-10
source: ArticleForge
keywords: [keyword1, keyword2, keyword3]
processed: 2026-04-19
---

Full article text starts here...
```

### CSV Export

For spreadsheet analysis:

```
Title,Author,Date,Source,Keywords,Notes
"Article Title","Author Name","2026-02-10","HBR","keyword1; keyword2","Processed: 2026-04-19"
```

## 📊 Command-Line Tools

### Process PDFs

```bash
# Full processing
python3 scripts/process_articles.py

# Preview without saving (dry-run)
python3 scripts/process_articles.py --dry-run

# Rebuild metadata from existing files
python3 scripts/process_articles.py --rebuild
```

### Search & Export

```bash
# Find by keyword
python3 scripts/query_metadata.py --by-keyword "artificial intelligence"

# Find by author
python3 scripts/query_metadata.py --by-author "Smith"

# List all articles
python3 scripts/query_metadata.py --list

# Show statistics
python3 scripts/query_metadata.py --stats

# Export to CSV
python3 scripts/query_metadata.py --export csv

# Export to JSON
python3 scripts/query_metadata.py --export json
```

### Zotero Export

```bash
# List articles ready for export
python3 scripts/zotero_export.py --list

# Export as CSV (for Zotero import)
python3 scripts/zotero_export.py --export csv

# Export as JSON (full metadata)
python3 scripts/zotero_export.py --export json

# Both formats
python3 scripts/zotero_export.py --export all
```

### Rename PDFs

```bash
# Preview rename operations
python3 scripts/rename_archived_pdfs.py --dry-run

# Apply renaming
python3 scripts/rename_archived_pdfs.py
```

### Migrate Formats

```bash
# Preview format migration
python3 scripts/migrate_to_source_format.py --dry-run

# Apply migration
python3 scripts/migrate_to_source_format.py
```

## 📦 Dependencies

All included in `requirements.txt`:

| Package | Version | Purpose |
|---------|---------|---------|
| pdfplumber | ≥0.9.0 | PDF text extraction with layout preservation |
| PyPDF2 | ≥3.0.0 | PDF metadata extraction |
| Pillow | ≥9.0.0 | Image processing for OCR |
| pytesseract | ≥0.3.10 | Optical character recognition |
| pdf2image | ≥1.16.0 | PDF to image conversion |
| numpy | ≥1.20.0 | Numerical operations (optional) |

### Installation Troubleshooting

```bash
# Update pip first
pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v

# For pytesseract, install Tesseract separately:
# macOS:  brew install tesseract
# Linux:  sudo apt-get install tesseract-ocr
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
```

## 📈 Performance

Processing times vary by PDF complexity:

| Batch Size | Typical Time |
|-----------|-------------|
| 1-10 PDFs | < 1 minute |
| 10-40 PDFs | 2-5 minutes |
| 40+ PDFs | 5-15 minutes |

Factors affecting speed:
- PDF file size
- Text density (articles vs. images)
- System resources
- OCR requirement for scanned PDFs

## 🔐 File Limits

- **PDF size**: Tested up to 50MB
- **Batch size**: 100+ PDFs (system-dependent)
- **Article length**: No practical limit
- **Registry entries**: Supports 1000+ articles

## 🎯 Use Cases

**Academic Research**
- Organize journal articles by publication
- Search articles by keywords or authors
- Export to citation managers (Zotero)

**Business Intelligence**
- Collect industry articles (ArticleForge, WSJ, Forbes)
- Track trends by keyword analysis
- Build searchable knowledge base

**Content Curation**
- Process large PDF collections
- Extract metadata automatically
- Create markdown library

**Knowledge Management**
- Organize personal reading
- Create taggable reference system
- Export to external tools

## 📚 Examples

### Example 1: Process a Batch of Articles

```bash
# 1. Copy PDFs to intake/
cp ~/Downloads/articles/*.pdf intake/

# 2. Run the system
./start.sh

# 3. Select option 1 (Process Articles)

# 4. Choose full processing

# 5. Check output/ folder for markdown files
ls output/ | head -5
# Output:
# 2026-02-10_HBR_Article_One.md
# 2026-02-10_Forbes_Article_Two.md
# 2025-12-09_WSJ_Article_Three.md
```

### Example 2: Search and Export

```bash
# Search for articles about "strategy"
python3 scripts/query_metadata.py --by-keyword "strategy"

# Export all to CSV for spreadsheet
python3 scripts/query_metadata.py --export csv

# View exported file
open metadata/articles_export.csv
```

### Example 3: Push to Zotero

```bash
# Via CLI
./start.sh
# Select: 5 (Export to Zotero)
# Choose: 1 (CSV format)

# Then in Zotero:
# File > Import > Select metadata/zotero_export.csv
```

## 🤝 Contributing

This is a personal/academic tool. Feel free to customize for your needs:

1. Add new publication sources to `extract_publication()`
2. Modify keyword extraction limits in `config.py`
3. Extend Zotero export with additional fields
4. Customize CLI colors and formatting

## 📝 License

Provided as-is for personal and academic use.

## 🔗 Related Tools

- [Zotero](https://www.zotero.org/) — Reference manager
- [pdfplumber](https://github.com/jsvine/pdfplumber) — PDF extraction
- [PyPDF2](https://github.com/py-pdf/PyPDF2) — PDF manipulation

## 📞 Support

### Debugging

Enable verbose output:
```bash
# Check Python version
python3 --version

# Verify dependencies
python3 -c "import pdfplumber; print(pdfplumber.__version__)"

# Run with error tracebacks
python3 scripts/process_articles.py 2>&1 | less
```

### Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: pdfplumber` | Dependency not installed | `pip install -r requirements.txt` |
| `Could not extract text` | PDF is corrupted or image-only | Use manual override |
| `Could not extract title` | Title not found in text | Use manual override |
| `No articles in registry` | No processing done yet | Process a PDF first |

---

**Version**: 1.0  
**Last Updated**: 2026-04-19  
**Status**: Production Ready ✓

**Questions?** Check the troubleshooting section or review the script comments for more details.
