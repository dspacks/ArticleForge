# Quick Start Guide: ArticleForge Article Processing

## 30-Second Setup

### 1. Install Dependencies

```bash
cd ArticleForge/scripts
pip install -r requirements.txt --break-system-packages
```

For OCR support on scanned PDFs:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS  
brew install tesseract

# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### 2. Run Processing (All PDFs are already in `intake/`)

```bash
python process_articles.py
```

The script will:
- Process 39 EBSCO ArticleForge PDFs from `intake/` folder
- Create markdown files in `output/` with YYYY-MM-DD naming
- Move PDFs to `pdf_archive/`
- Generate `metadata/articles_metadata.json`

**Expected output:**
```
======================================================================
ArticleForge Article Processing Pipeline
Found 39 PDF(s) to process
======================================================================

Processing: EBSCO-FullText-04_18_2026 (1).pdf
  → Extracting text...
  → Extracting metadata...
  ✓ Wrote: 2024-03-15_Article_Title.md
  ✓ Archived: EBSCO-FullText-04_18_2026 (1).pdf

[... processing continues for all 39 files ...]

======================================================================
PROCESSING SUMMARY
======================================================================
Total processed:  39
Successful:       38
Failed:           1
Skipped:          0
======================================================================
✓ Output files: ./output
✓ Archived PDFs: ./pdf_archive
✓ Metadata registry: ./metadata/articles_metadata.json
```

### 3. Explore Your Results

**See all articles:**
```bash
python query_metadata.py --list
```

**Show statistics:**
```bash
python query_metadata.py --stats
```

**Find articles about a topic:**
```bash
python query_metadata.py --by-keyword strategy
```

**Export to CSV (for Excel):**
```bash
python query_metadata.py --export csv
```

## What You Get

### Output Folder Structure

```
output/
├── 2024-03-15_The_Future_of_Artificial_Intelligence.md
├── 2024-03-20_Digital_Transformation_Strategy.md
├── 2024-04-01_Leadership_in_Uncertain_Times.md
└── ... (38 more files)
```

### Example Markdown File

```markdown
---
title: The Future of Artificial Intelligence
author: Andrew McAfee
date: 2024-03-15
keywords: [artificial intelligence, machine learning, business, transformation]
processed: 2024-04-19
---

The future of artificial intelligence in business is not about replacing 
humans with machines. Instead, it's about augmenting human capabilities...

[Full article text here]
```

### Metadata Registry

`metadata/articles_metadata.json` contains:
- All article titles, authors, dates
- Automatically extracted keywords for each article
- Processing status and timestamps
- Article file locations

Use this to search across all articles!

## Common Commands

```bash
# Preview without writing files
python process_articles.py --dry-run

# Rebuild metadata if you manually edit markdown files
python process_articles.py --rebuild

# Search by author
python query_metadata.py --by-author "Michael Porter"

# Find articles from March 2024
python query_metadata.py --by-keyword "march" --list

# Export as JSON for integration
python query_metadata.py --export json
```

## Folder Guide

| Folder | Purpose |
|--------|---------|
| `intake/` | PDFs waiting to be processed (39 files ready) |
| `output/` | Processed markdown files (created during first run) |
| `pdf_archive/` | Original PDFs after processing |
| `metadata/` | JSON registry of all processed articles |
| `scripts/` | Python processing scripts |

## Troubleshooting

**"ModuleNotFoundError: No module named 'pdfplumber'"**
```bash
pip install pdfplumber pytesseract pdf2image pillow --break-system-packages
```

**"pytesseract.TesseractNotFoundError"** (OCR issue)

Tesseract isn't installed. Run:
- Ubuntu: `sudo apt-get install tesseract-ocr`
- macOS: `brew install tesseract`
- Windows: https://github.com/UB-Mannheim/tesseract/wiki

**Need more help?**

See `README.md` for:
- Detailed configuration options
- Advanced usage patterns  
- Performance optimization
- Custom keyword extraction
- Automated scheduling

## Next Steps

1. ✅ Install requirements
2. ✅ Run `python process_articles.py`
3. ✅ Check `output/` for generated markdown files
4. ✅ Query results with `python query_metadata.py --stats`
5. 📖 Read `README.md` for advanced features

---

**Processing 39 articles takes ~2-5 minutes depending on PDF complexity and OCR needs.**
