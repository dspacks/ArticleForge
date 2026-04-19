# ArticleForge Article System — Interactive CLI Guide

## Quick Start

### Run the Interactive Interface

**Linux/macOS:**
```bash
cd ArticleForge
./start.sh
```

**Windows (PowerShell):**
```powershell
cd ArticleForge
python hbr.py
```

---

## Main Menu Options

### 1️⃣ Process Articles
Extract PDFs from `intake/` folder and convert to markdown files.

- **Full Processing**: Extracts text, detects metadata, creates markdown, archives PDFs
- **Dry Run**: Preview what would happen without saving changes

**When to use**: 
- You've added new PDFs to the `intake/` folder
- You want to batch process multiple articles
- You're testing the extraction pipeline

---

### 2️⃣ Search Articles
Find articles by keyword or author across your collection.

**Options:**
- **By Keyword**: Search extracted keywords (e.g., "AI", "leadership", "strategy")
- **By Author**: Find articles by specific author names
- **List All**: Show all 39 processed articles with metadata

**Examples:**
```
Search "artificial intelligence" → Returns all articles with AI keywords
Search "Nelson" → Returns articles by Ryan Nelson
```

---

### 3️⃣ View Statistics
Show comprehensive metadata and keyword analysis.

**Displays:**
- Total article count
- Unique authors
- Top keywords by frequency
- Date range coverage
- Average article length
- Author distribution

---

### 4️⃣ Export Data
Export article metadata for use in Excel, analytics, or other tools.

**Export Formats:**
- **CSV**: Open in Excel, Google Sheets, etc.
  - Columns: Title, Author, Date, Keywords, File, Length
- **JSON**: Raw data format for integration with other systems

**Files Created:**
- `metadata/articles_export.csv`
- `metadata/articles_export.json`

---

### 5️⃣ Manage Manual Overrides
Handle metadata for articles that failed automatic extraction.

**What are overrides?**
Sometimes PDF metadata is unusual or embedded in non-standard ways. Manual overrides let you provide titles/authors directly.

**Options:**
- **View Current**: See all manually added metadata
- **Add New**: Create override for a problem PDF
- **Edit File**: Manually edit `manual_metadata_overrides.json`

**Example:**
```json
{
  "source_file": "EBSCO-FullText-04_18_2026 (27).pdf",
  "title": "Why the Digital Product Model Beats Project-Based Approaches",
  "author": "Ryan Nelson and Thomas H. Davenport",
  "date": "2026-02-10"
}
```

---

### 6️⃣ Rename PDFs
Rename archived PDFs to match markdown filenames (`YYYY-MM-DD_Title.pdf`).

**Options:**
- **Rename All**: Apply naming to all PDFs
- **Preview (Dry-run)**: See what would be renamed without making changes

**Before:** `EBSCO-FullText-04_18_2026 (1).pdf`
**After:** `2026-02-10_Why the Digital Product Model Beats Project-Based Approaches.pdf`

---

### 7️⃣ List All Articles
Display all 39 processed articles in chronological order.

Shows:
- Article title
- Author (if detected)
- Publication date
- Keywords
- File size

---

### 8️⃣ Quick Preview
Sample text from any article without opening files.

- Shows first 1,000 characters of article text
- Preview of markdown formatting
- Quick way to verify content

---

### 9️⃣ Settings
View system configuration and file locations.

**Displays:**
- Base directory
- Output folder location
- Archive folder location
- Metadata folder location
- Last update timestamp

---

### 0️⃣ Exit
Quit the program.

---

## Dashboard

The dashboard at the top of each screen shows:

```
● Markdown Files:    32       (Processed articles)
● Archived PDFs:     39       (Original PDFs, archived)
● Intake PDFs:       0        (New PDFs waiting to process)
● Total Articles:    39       (All articles in system)
● Unique Keywords:   99       (Searchable keywords)
```

---

## Workflow Examples

### Workflow 1: Process New Articles

```
1. Add PDFs to intake/ folder
2. Run Menu → Option 1 (Process Articles)
3. Select "Full processing"
4. Wait for completion
5. Check Menu → Option 7 to verify
```

### Workflow 2: Search & Export

```
1. Menu → Option 2 (Search)
2. Search for keyword: "data"
3. Menu → Option 4 (Export)
4. Choose CSV format
5. Open articles_export.csv in Excel
```

### Workflow 3: Fix Problem Article

```
1. Menu → Option 5 (Manual Overrides)
2. View current overrides
3. Add new override with PDF filename + title
4. Menu → Option 1 (Process Articles)
5. Article now processes correctly
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `0` | Return to main menu |
| `Ctrl+C` | Exit program (any time) |
| `Enter` | Confirm selection |

---

## File Organization

After using the CLI, your folder structure looks like:

```
ArticleForge/
├── hbr.py                 (Main CLI interface)
├── start.sh               (Launcher script)
├── output/                (Processed markdown files)
├── pdf_archive/           (Original PDFs, renamed)
├── intake/                (New PDFs to process)
└── metadata/              (Metadata registry + exports)
```

---

## Troubleshooting

**"No PDFs found in intake/"**
- Place PDF files in the `intake/` folder
- Ensure they have `.pdf` extension

**"Could not extract article title"**
- Use Menu → Option 5 to add manual metadata override
- Provides title + author directly

**Processing takes too long**
- Large PDFs with complex layouts take longer
- OCR (for scanned PDFs) adds processing time
- Use dry-run first to see estimate

**Export file not created**
- Ensure you have the `metadata/` folder
- Check folder permissions
- Try again from Menu → Option 4

---

## Tips & Tricks

### 💡 Search Efficiency
- Start with short keywords: "AI" instead of "artificial intelligence"
- Search common topics: "leadership", "strategy", "data", "innovation"
- Use author names for targeted searches

### 💡 Organization
- Export to CSV monthly for archival
- Use Excel filters on exported CSV
- Sort by date to track content over time

### 💡 Batch Operations
- Process 10+ articles at once
- Use dry-run to preview extraction quality
- Fix any issues before full processing

### 💡 Maintenance
- Check "Intake PDFs" count weekly
- Run statistics monthly to track growth
- Keep manual overrides file updated

---

## Advanced Usage

### Command Line (Advanced Users)

For power users, you can also use the underlying scripts directly:

```bash
# Process with dry-run
cd scripts
python process_articles.py --dry-run

# Search with filters
python query_metadata.py --by-keyword "strategy"

# Export to CSV
python query_metadata.py --export csv

# View all statistics
python query_metadata.py --stats
```

### Extending the System

The CLI is designed to be extended. To add new features:

1. Add method to `ArticleForgeCLi` class in `hbr.py`
2. Add menu option in `show_menu()`
3. Call your method from `run()` loop

---

## System Requirements

- Python 3.7+
- Linux, macOS, or Windows
- 100MB free disk space
- Terminal/Command Prompt

---

**Version**: 1.0
**Last Updated**: 2026-04-19
**Status**: Production Ready ✅
