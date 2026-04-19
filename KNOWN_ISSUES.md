# Known Issues — ArticleForge Article Processing System

**Generated:** 2026-04-19  
**Test suite run:** 175 tests — 174 passed, 1 confirmed bug, several additional issues found through static code review.

---

## CONFIRMED BUGS (test-verified)

---

### BUG-001 — `find_by_author` crashes when `author` field is `None`

**Severity:** HIGH  
**File:** `scripts/query_metadata.py`, line 102  
**Failing test:** `TestQueryMetadata::test_find_by_author_none_value`

**Description:**  
When an article in the registry has `"author": null` (which happens legitimately when no author can be extracted from a PDF), the author search crashes with:

```
AttributeError: 'NoneType' object has no attribute 'lower'
```

**Reproducer:**
```python
registry = {"articles": [{"title": "Test", "author": None, "keywords": []}]}
find_by_author(registry, "Smith")  # AttributeError
```

**Root Cause:**  
Line 102 uses `a.get('author', '').lower()` — but `a.get('author', '')` returns `None` (not `''`) when the stored value is explicitly `null`. The default `''` is only applied when the key is absent entirely.

**Fix:**  
```python
results = [a for a in articles if author.lower() in (a.get('author') or '').lower()]
```

---

## ISSUES FOUND VIA STATIC CODE REVIEW (not yet triggering crashes in current data)

---

### BUG-002 — YAML frontmatter not properly escaped — titles with colons break YAML

**Severity:** HIGH  
**File:** `scripts/utils.py`, `create_markdown_content()`, lines 511–534

**Description:**  
The YAML frontmatter is built by plain string concatenation. Any article title (or author name) containing a colon (`:`) produces invalid YAML because the parser will treat everything after the colon as a nested key. Titles like `"Leadership: The Missing Ingredient"` produce:

```yaml
title: Leadership: The Missing Ingredient
```

This is syntactically invalid YAML. A YAML parser expecting this block will either silently truncate the title or raise `ScannerError`.

**Real-World Impact:**  
The `rebuild_registry()` function re-parses YAML frontmatter from markdown files. Any article whose title contains a colon will have its title corrupted during rebuild — the registry will only record `"Leadership"` as the title, losing everything after the colon.

**Evidence from real data:**  
The live registry contains titles that are incomplete sentence fragments ("Although Bill thought of himself as a"), strongly suggesting the title extraction and YAML storage is already mishandling content in some cases.

**Fix:**  
Wrap values in YAML-safe quotes:
```python
frontmatter.append(f'title: "{title.replace(chr(34), chr(39))}"')
```
Or use a proper YAML serializer (`import yaml; yaml.dump(...)`).

---

### BUG-003 — `rebuild_registry()` YAML parser is fragile — breaks on any `: ` in value

**Severity:** HIGH  
**File:** `scripts/process_articles.py`, `rebuild_registry()`, lines 288–297

**Description:**  
The manual YAML parsing loop:
```python
if ': ' in line:
    key, value = line.split(': ', 1)
```
This correctly uses `split(': ', 1)` for the _first_ colon, but the issue is upstream: if the stored `title:` value itself contains `: ` (which is legal content but illegal unquoted YAML), the frontmatter was never written with quotes (see BUG-002), so the value in the file is already truncated at write time.

Additionally, the keywords parser:
```python
if key == 'keywords':
    value = value.strip('[]').split(', ')
```
…will silently produce wrong results if any keyword contains a comma or bracket.

---

### BUG-004 — `sanitize_filename` does not enforce length limits

**Severity:** MEDIUM  
**File:** `scripts/utils.py`, `sanitize_filename()`, lines 469–486

**Description:**  
There is no maximum filename length cap. The generated output filenames follow the pattern `{date}_{source}_{safe_title}.md`. If a PDF metadata title is very long (common in scholarly databases), the resulting filename can exceed the filesystem's 255-byte limit (ext4, NTFS). This causes a silent `FileNotFoundError` or `OSError` when the file is written.

**Example:**  
An article titled `"A Comprehensive Review of Transformational Leadership Theory and Its Applications in Modern Organizational Behavioral Science Settings"` produces a filename that exceeds 255 chars when prefixed with date and source.

**Fix:**  
```python
MAX_FILENAME_LEN = 200
sanitized = sanitized[:MAX_FILENAME_LEN].rstrip()
```

---

### BUG-005 — `_add_override` validation allows `source_file` to be empty while still saving

**Severity:** MEDIUM  
**File:** `processing_ui.py`, `_add_override()`, lines 376–405

**Description:**  
The validation check is:
```python
if not all([source_file, title, date]):
    self.print_error("Title and date are required")
    return
```
The `all([...])` check correctly requires `source_file`, `title`, and `date` to be non-empty — but the error message only says "Title and date are required", making the validation requirement for `source_file` invisible to the user. If `source_file` is left blank, the error fires with a misleading message.

More critically, the override is keyed by `source_file` in `load_manual_overrides()`. A blank `source_file` creates an override with key `""` that matches no PDF, silently wasting the entry.

---

### BUG-006 — `get_stats()` silently swallows all JSON errors with bare `except:`

**Severity:** LOW-MEDIUM  
**File:** `processing_ui.py`, `get_stats()`, lines 87–96

**Description:**  
```python
try:
    with open(metadata_file, 'r') as f:
        ...
except:
    pass
```
A bare `except:` catches _everything_, including `KeyboardInterrupt`, `SystemExit`, `MemoryError`, and `PermissionError`. The user gets no feedback if the registry is unreadable due to permissions or disk errors — the dashboard just silently shows 0 everywhere.

The same pattern appears in `menu_zotero_export()` (line 273) and `_add_override()` (line 384–386).

---

### BUG-007 — `_run_processor()` and `_run_rename()` do not capture stderr

**Severity:** MEDIUM  
**File:** `processing_ui.py`, lines 171–186, 431–441

**Description:**  
Both methods call `subprocess.run(cmd, ...)` without `capture_output` or `stderr=subprocess.PIPE`. If the subprocess crashes with a Python traceback, the raw traceback dumps into the terminal unstyled, looking like a crash to the user even if the CLI wrapper tries to show a clean error afterward.

The return code is checked in `_run_processor()` but not in `_run_rename()` — a rename failure produces no user-visible error from the UI layer.

---

### BUG-008 — `extract_text_from_pdf()` raises `ImportError` if `pdfplumber` is missing, instead of returning empty string

**Severity:** MEDIUM  
**File:** `scripts/utils.py`, lines 131–132

**Description:**  
```python
if not PDFPLUMBER_AVAILABLE:
    raise ImportError("pdfplumber is required...")
```
This `ImportError` is caught by the broad `except Exception as e:` in `process_pdf()`, which then returns `None` (counts as a failed article). The user sees "Error: pdfplumber is required" buried in the traceback output. There is no top-level pre-flight check that validates all dependencies before starting the batch. Processing 50 PDFs then encountering this error on all of them gives a very bad UX.

---

### BUG-009 — Concurrent access not protected — two simultaneous runs corrupt the metadata registry

**Severity:** MEDIUM  
**File:** `scripts/process_articles.py`, `save_metadata_registry()`, lines 73–82

**Description:**  
The metadata registry is a plain JSON file written with no file locking. If two processes (e.g., the user runs the CLI twice in different terminals) run simultaneously, the last writer wins and whichever process saved first loses all its additions. There is no atomic write pattern (write-to-temp then rename).

---

### BUG-010 — `parse_metadata_from_filename` date field name collision with PDF metadata

**Severity:** LOW  
**File:** `scripts/utils.py`, `parse_metadata_from_filename()`, lines 573–593  
**Also:** `scripts/process_articles.py`, lines 138–183

**Description:**  
`parse_metadata_from_filename()` returns `{"source": "EBSCO", "export_date": "2026-04-18"}`. This dict is then used via:
```python
metadata_entry.update(filename_metadata)
```
The `export_date` key is added to the article's metadata entry. However, `export_date` is the EBSCO download date, NOT the article publication date. These are different concepts and the field name could mislead users querying the metadata registry.

Additionally, if `filename_metadata` ever returned a key like `"source"`, it would silently overwrite the `source` field that was already set from text extraction.

---

### BUG-011 — `detect_table_or_sidebar_line` matches dollar amounts and percentages everywhere, misclassifying body text

**Severity:** LOW  
**File:** `scripts/utils.py`, `detect_table_or_sidebar_line()`, lines 283–285

**Description:**  
```python
if re.search(r'\d+\s+\d+|\d+\s*%|\$\d+', line):
    return True
```
Any sentence mentioning percentages or dollar amounts (e.g., "Companies saw a 40% improvement" or "The $2 trillion market") is classified as sidebar/table content and demoted out of the main text flow. This artificially removes quantitative claims from article bodies, degrading keyword extraction and text completeness.

---

### BUG-012 — `extract_title` and `extract_author` operate on only the first 500/1000 chars, but the pattern that flags "Author:" or "By" may match running text

**Severity:** LOW  
**File:** `scripts/utils.py`, lines 329–337, 360–377

**Description:**  
The `By` pattern:
```python
re.search(r'[Bb]y\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', search_text)
```
...matches phrases like "by John Smith" which appear naturally in body text ("A study conducted by John Smith showed..."). This may extract a cited author rather than the article's actual author, with no way to distinguish the two.

---

### BUG-013 — `PyPDF2` is deprecated and triggers a DeprecationWarning on every import

**Severity:** LOW  
**File:** `scripts/utils.py`, line 28; `scripts/requirements.txt`

**Description:**  
The library `PyPDF2` was deprecated in favour of `pypdf` and shows a `DeprecationWarning: PyPDF2 is deprecated` on every run. The `requirements.txt` pins `PyPDF2>=3.0.0`. While this doesn't break functionality today, the library will eventually stop receiving security updates. The warning also pollutes the CLI output.

---

## SUMMARY TABLE

| ID      | Description                                       | Severity | Confirmed by Test |
|---------|---------------------------------------------------|----------|-------------------|
| BUG-001 | `find_by_author` crashes on `null` author         | HIGH     | YES               |
| BUG-002 | Colons in titles break YAML frontmatter           | HIGH     | Partial (no crash)|
| BUG-003 | `rebuild_registry` YAML parser is fragile         | HIGH     | Partial           |
| BUG-004 | No filename length limit — can exceed 255 bytes   | MEDIUM   | No (needs long title)|
| BUG-005 | Misleading error message in `_add_override`       | MEDIUM   | Partial           |
| BUG-006 | Bare `except:` swallows all errors silently       | MEDIUM   | No                |
| BUG-007 | Subprocess stderr not captured in CLI             | MEDIUM   | No                |
| BUG-008 | No pre-flight dependency check before batch       | MEDIUM   | No                |
| BUG-009 | No file locking — concurrent access corrupts data | MEDIUM   | No                |
| BUG-010 | `export_date` vs publication `date` confusion     | LOW      | No                |
| BUG-011 | `%` and `$` patterns misclassify body text        | LOW      | No                |
| BUG-012 | "By Name" pattern matches cited authors too       | LOW      | No                |
| BUG-013 | `PyPDF2` deprecated — use `pypdf` instead         | LOW      | Yes (warning)     |
