# CLI Usage Guide

The Article Processing System can be invoked multiple ways depending on your setup and preferences.

## Method 1: Direct Launch (Easiest)

From within the project directory:

```bash
# Using shell script
./start.sh

# Or directly with Python
python3 processing_ui.py
```

## Method 2: Module Invocation

Run from any directory using Python's module system:

```bash
# Interactive CLI
python3 -m hbr_system

# Or with specific mode
python3 -m hbr_system --mode search --query "artificial intelligence"
```

**Requires:** Python 3.8+, dependencies installed (`pip install -r requirements.txt`)

## Method 3: Standalone Executable (Linux/macOS)

Use the provided CLI wrapper:

```bash
# From project directory
./hbr-cli

# With arguments
./hbr-cli --mode stats
./hbr-cli --mode search --by author --query "Smith"
```

**Requires:** Execute permission (`chmod +x hbr-cli`)

## Method 4: Installed as Package

Install the system globally:

```bash
# Development mode (symlinks to source)
pip install -e /path/to/article-processing-system

# Normal installation
pip install /path/to/article-processing-system

# Then use from anywhere
hbr-cli
hbr-cli --mode process --dry-run
hbr-cli --mode export --format json
```

## Command-Line Modes

### Interactive CLI (Default)

```bash
./start.sh
# OR
python3 processing_ui.py
# OR  
python3 -m hbr_system
```

Launches the interactive menu system. All options available through the menu.

### Batch Processing Mode

```bash
python3 -m hbr_system --mode process --dry-run
```

Processes all PDFs in `intake/` folder:
- `--dry-run`: Preview without saving
- Useful for automation and scripting

### Search Mode

```bash
python3 -m hbr_system --mode search --query "machine learning"
python3 -m hbr_system --mode search --by author --query "Smith"
```

Search options:
- `--query TEXT`: Search string
- `--by {keyword|author}`: Search type (default: keyword)

### Export Mode

```bash
python3 -m hbr_system --mode export --format bibtex
python3 -m hbr_system --mode export --format csv
python3 -m hbr_system --mode export --format json
```

Export options:
- `--format {bibtex|csv|json}`: Export format (bibtex recommended for Zotero)

### Statistics Mode

```bash
python3 -m hbr_system --mode stats
```

Display article statistics and keyword analysis.

## Advanced Usage

### Batch Processing in Scripts

```bash
#!/bin/bash
# Process articles in background
cd /path/to/article-processing-system

# Copy PDFs to intake
cp ~/Downloads/articles/*.pdf intake/

# Process with dry-run first
python3 -m hbr_system --mode process --dry-run

# If dry-run looks good, process for real
python3 scripts/process_articles.py

# Export results
python3 -m hbr_system --mode export --format csv

# Copy results elsewhere
cp metadata/articles_export.csv ~/reports/
```

### Cron Job (Automated Processing)

```bash
# Add to crontab -e
0 2 * * * cd /path/to/system && python3 -m hbr_system --mode process >> /tmp/hbr.log 2>&1
```

Processes articles daily at 2 AM.

### Direct Script Import

```python
# In your own Python code
import sys
sys.path.insert(0, "/path/to/article-processing-system/scripts")

from process_articles import ArticleProcessor
from query_metadata import load_registry, find_by_keyword

# Process articles
processor = ArticleProcessor()
processor.process_all()

# Search results
registry = load_registry()
results = find_by_keyword(registry, "AI")
for article in results:
    print(article['title'])
```

## Help and Options

```bash
# Show all available options
python3 -m hbr_system --help

# Show help for specific mode
python3 -m hbr_system --mode search --help
```

## Environment Variables

Set before running:

```bash
# Control output directory
export HBR_OUTPUT_DIR=/custom/path/output

# Enable debug mode
export HBR_DEBUG=1

# Set custom metadata location
export HBR_METADATA_DIR=/custom/path/metadata

# Run with variables
HBR_DEBUG=1 python3 processing_ui.py
```

## Integration Examples

### With Other Tools

**Export to Zotero (Recommended: BibTeX)**
```bash
# Export as BibTeX (best format for Zotero)
python3 -m hbr_system --mode export --format bibtex

# Then import into Zotero (GUI)
# File → Import → metadata/articles_export.bib
```

**Alternative Formats:**
```bash
# CSV format (Excel-compatible)
python3 -m hbr_system --mode export --format csv

# JSON format (full metadata)
python3 -m hbr_system --mode export --format json
```

**Send to Email**
```bash
# Process, export, and email
python3 scripts/process_articles.py
python3 -m hbr_system --mode export --format csv
mail -s "Weekly Articles" user@example.com < metadata/articles_export.csv
```

**Integrate with Web App**
```python
# Flask example
from flask import Flask, jsonify
from query_metadata import load_registry, find_by_keyword

app = Flask(__name__)

@app.route('/search')
def search():
    query = request.args.get('q')
    registry = load_registry()
    results = find_by_keyword(registry, query)
    return jsonify(results)
```

## Troubleshooting

### "Command not found: hbr-cli"

**Solution:** Use full path or install as package
```bash
/full/path/to/hbr-cli
# OR
pip install -e /path/to/system
```

### "ModuleNotFoundError: No module named..."

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### "Permission denied: ./hbr-cli"

**Solution:** Make executable
```bash
chmod +x hbr-cli
```

### Changes not reflecting

**Solution:** Ensure you're running from the correct directory or have installed the package

```bash
# Check which version is running
which hbr-cli
python3 -c "import hbr_system; print(hbr_system.__file__)"
```

## Performance Tips

1. **For large batches**, use `--mode process --dry-run` first to verify
2. **Schedule heavy processing** during off-hours with cron
3. **Export to CSV** (faster) for most use cases; use JSON only when needed
4. **Search locally** before exporting to reduce data transfer

## Next Steps

- See **README.md** for complete documentation
- See **TESTING.md** for test suite and validation
- See **KNOWN_ISSUES.md** for any known limitations
- Review **recommendations.txt** for hardening suggestions
