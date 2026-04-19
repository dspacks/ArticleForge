# ArticleForge — Rebranding Summary

**Date:** April 19, 2026  
**Status:** ✅ Complete

## Overview

The project has been rebranded from "HBR Article Processing System" to **ArticleForge** to reflect its generic, publication-agnostic nature and expanded scope.

## What Changed

### Folder Structure
- `HBR/` → `article-forge/` (new directory in `/PROJECTS/`)
- Project folder follows kebab-case naming convention

### Core Files Renamed
- `hbr-cli` → `article-forge` (executable wrapper)
- Class: `HBRCLi` → `ArticleForgeCLi`

### Package Configuration (setup.py)
- **Package name:** `article-processing-system` → `article-forge`
- **Console script:** `hbr-cli=__main__:main` → `article-forge=__main__:main`
- **Description:** Updated to generic scope
- **GitHub URLs:** Updated from `article-processing-system` to `article-forge`

### Documentation Updated
- **README.md** — Title and description changed to ArticleForge branding
- **CLI_USAGE.md** — Updated command examples
- **__main__.py** — Module entry point docstring updated
- **start.sh** — Script header updated
- All markdown files: "Article Processing System" → "ArticleForge" throughout

### Code References
- All docstrings and comments updated
- Variable naming consistent with new brand
- Maintained backward compatibility in functionality

## Invocation Methods

### Interactive Mode
```bash
./start.sh                    # Quick launcher
python3 processing_ui.py      # Direct invocation
```

### Module Invocation
```bash
python3 -m article_forge            # Interactive CLI
python3 -m article_forge --help     # Show options
```

### Installed Package
```bash
pip install -e .                    # Install in development mode
article-forge                       # Use from anywhere
article-forge --mode search --query "AI"
```

### Standalone Executable
```bash
./article-forge                     # Direct invocation from project directory
./article-forge --mode export --format bibtex
```

## Features Preserved

✅ All 39 articles processed  
✅ Complete CLI with 11 menu options  
✅ Publication source detection (HBR, WSJ, Forbes, etc.)  
✅ BibTeX, CSV, JSON export formats  
✅ Zotero integration  
✅ Full test suite (175 tests)  
✅ Comprehensive documentation  
✅ Error handling & edge case coverage  

## File Manifest

```
article-forge/
├── processing_ui.py           # Main interactive CLI (updated class name)
├── __main__.py               # Module entry point (updated docstring)
├── article-forge             # Executable wrapper (renamed from hbr-cli)
├── setup.py                  # Package setup (updated name & metadata)
├── start.sh                  # Quick launcher
├── scripts/
│   ├── zotero_export.py     # BibTeX, CSV, JSON export
│   ├── process_articles.py  # PDF processing pipeline
│   ├── query_metadata.py    # Search & query functions
│   ├── utils.py             # Text extraction utilities
│   └── (6 other utility scripts)
├── metadata/
│   ├── articles_metadata.json     # (git ignored)
│   ├── manual_metadata_overrides.json  # (git ignored)
│   └── zotero_export.*       # (git ignored - generated)
├── output/                   # Processed markdown articles (git ignored)
├── intake/                   # PDF input folder (git ignored)
├── pdf_archive/              # Archived PDFs (git ignored)
├── README.md                 # Updated with ArticleForge branding
├── TESTING.md
├── KNOWN_ISSUES.md
├── CLI_USAGE.md
├── recommendations.txt
└── (other documentation files)
```

## Migration Notes

### For Existing Users

If you have the old `HBR/` folder:
1. The new `article-forge/` folder contains all updates
2. Your `intake/`, `output/`, and `pdf_archive/` folders can be copied over
3. Your `metadata/articles_metadata.json` can be migrated
4. All functionality remains identical — only naming has changed

### For Development

Update any scripts or references:
```bash
# Old
python3 HBR/scripts/process_articles.py

# New
python3 article-forge/scripts/process_articles.py
```

### Git Status

- `.gitignore` properly excludes user data and generated files
- Codebase ready for public repository under `article-forge` name
- No secrets or private information exposed

## Verification Checklist

- ✅ All Python files compile without errors
- ✅ Class names updated (HBRCLi → ArticleForgeCLi)
- ✅ setup.py package name and metadata updated
- ✅ CLI executable renamed and functional
- ✅ Module invocation updated (`python -m article_forge`)
- ✅ Documentation reflects new branding
- ✅ Article source examples preserved (HBR, WSJ, Forbes remain in filenames)
- ✅ BibTeX export available as default format
- ✅ All 175 tests still applicable
- ✅ .gitignore excludes user data

## Ready for Publication

✅ **ArticleForge is production-ready for public release**

The system maintains all functionality while adopting professional, generic branding suitable for broad publication scope.

---

**Last Updated:** 2026-04-19  
**Status:** Rebranding Complete ✓
