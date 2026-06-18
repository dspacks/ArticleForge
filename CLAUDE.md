# ArticleForge — Technical Context

_Last updated: 2026-04-25_

## Purpose

A robust article extraction and processing engine, specifically optimized for Harvard Business Review (HBR) content. Handles PDF archiving, metadata enrichment (Zotero integration), and automated summary generation.

## Architecture

### Stack
- **Language:** Python 3.10+
- **Key dependencies:** PyPDF2/pdfminer (extraction), Pydantic, pytest

### Key Files
- `processing_ui.py` — Main CLI/GUI for article processing
- `__main__.py` — Entry point
- `scripts/` — Support scripts for extraction and metadata
- `intake/` — Drop zone for new articles
- `output/` — Processed results and summaries

## Setup

### Prerequisites
- Python 3.10+
- Zotero (optional, for metadata sync)

### Installation
```bash
cd projects/ArticleForge
pip install -e .
```

### Running Tests
```bash
pytest test_suite.py
```

## Development Workflow

### CLI Usage
```bash
./hbr-cli [command]
# or
python processing_ui.py
```

## Key Decisions

- **Unified CLI:** The `hbr-cli` wrapper provides a single entry point for complex extraction tasks.
- **Metadata-First:** Prioritizes high-quality metadata (Zotero-compatible) over simple text extraction.
- **Archive Strategy:** Maintains a `pdf_archive/` to ensure source availability for re-processing.

## Current Status

- **Phase:** Stable / Rebranded (formerly HBR project)
- **Known Issues:** See `KNOWN_ISSUES.md` for specific extraction edge cases.

## Next Steps

1. Integrate with LLM for enhanced semantic analysis.
2. Automate Zotero collection filing.
3. Improve PDF table extraction.

## Quick Reference

- **Test command:** `pytest`
- **Main entry:** `processing_ui.py`
- **User Guide:** `CLI_GUIDE.md` / `QUICKSTART.md`
