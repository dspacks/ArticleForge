# TESTING.md — ArticleForge Article Processing System

**Test Suite Location:** `/sessions/dazzling-epic-carson/mnt/PROJECTS/ArticleForge/test_suite.py`  
**Test Framework:** pytest  
**Python Version Tested:** 3.10.12  
**Total Tests:** 175  
**Pass Rate (baseline):** 174/175 (99.4%) — 1 confirmed bug found

---

## How to Run the Tests

### Install pytest (one time)
```bash
pip install pytest
```

### Run all tests
```bash
# From project root
pytest test_suite.py -v

# With short tracebacks (recommended for CI)
pytest test_suite.py -v --tb=short

# Run a specific class
pytest test_suite.py::TestSanitizeFilename -v

# Run a specific test
pytest test_suite.py -v -k "test_find_by_author_none_value"

# Run and stop on first failure
pytest test_suite.py -v -x
```

### Expected output (clean run after BUG-001 is fixed)
```
175 passed in ~1.2s
```

---

## Test Structure Overview

The suite is organized into 20 test classes covering the entire codebase:

| Section | Class                         | What It Tests                                         | Count |
|---------|-------------------------------|-------------------------------------------------------|-------|
| 1       | `TestSanitizeFilename`        | All invalid-char cases, edge strings, unicode         | 18    |
| 2       | `TestExtractTitle`            | PDF metadata priority, text fallback, rejection rules | 9     |
| 3       | `TestExtractAuthor`           | Metadata priority, regex patterns, null inputs        | 9     |
| 4       | `TestExtractDate`             | All date formats, leap year, invalid inputs           | 10    |
| 5       | `TestExtractKeywords`         | Stopwords, dedup, count, sorted output, unicode       | 12    |
| 6       | `TestExtractPublication`      | All known markers, case sensitivity, position limit   | 11    |
| 7       | `TestParseMetadataFromFilename` | EBSCO pattern, partial match, empty input             | 6     |
| 8       | `TestCreateMarkdownContent`   | YAML frontmatter correctness, all field combinations  | 11    |
| 9       | `TestCleanExtractedText`      | Page break removal, camelCase split, hyphen handling  | 8     |
| 10      | `TestArticleProcessor`        | Registry load/save, dry run, overrides, rebuild       | 13    |
| 11      | `TestQueryMetadata`           | Load, search by keyword/author, stats, CSV export     | 8     |
| 12      | `TestZoteroExport`            | Format for Zotero, CSV/JSON export, empty inputs      | 7     |
| 13      | `TestRenamePDFs`              | Dry run, real rename, collision avoidance, missing    | 5     |
| 14      | `TestEdgeCases`               | Cross-function edge cases, pathological inputs        | 10    |
| 15      | `TestDataIntegrity`           | Schema validation, no duplicates, round-trips         | 6     |
| 16      | `TestCLILayer`                | Stats, overrides UI, quick preview, Zotero menu       | 11    |
| 17      | `TestFileSystemEdgeCases`     | Missing dirs, non-PDF files, auto-create dirs         | 4     |
| 18      | `TestEncodingEdgeCases`       | UTF-8 write/read, accented chars, JSON round-trip     | 4     |
| 19      | `TestConfig`                  | Stopwords set, date formats, path types, schema       | 5     |
| 20      | `TestRegressionCases`         | Live registry and real output file validation         | 6     |

---

## Test Plan: Edge Cases Coverage

### 1. Empty and Missing Directories

**Scenario:** Processing triggered when intake/ is empty.  
**Test:** `TestArticleProcessor::test_process_all_empty_intake`  
**Expected:** Clean message printed, no crash, stats show 0 processed.

**Scenario:** Output directory is deleted before write.  
**Test:** `TestFileSystemEdgeCases::test_output_dir_missing_on_write`  
**Expected:** FileNotFoundError raised and caught gracefully.

---

### 2. Corrupted and Empty PDFs

**Scenario:** A .pdf file contains garbage bytes.  
**Coverage:** `fake_pdf`, `corrupted_pdf`, `empty_pdf` fixtures. The `process_pdf()` pipeline catches all exceptions via `except Exception` and returns `None`. The test confirms this increments `failed` not `successful`.  
**Gap:** pdfplumber may partially succeed on some corrupted files and return < 100 chars of text, which is caught by the `len(text) < 100` guard.

---

### 3. Missing Dependencies

**Scenario:** `pdfplumber` not installed.  
**Coverage:** `TestArticleProcessor` — the module-level availability flags (`PDFPLUMBER_AVAILABLE` etc.) are tested implicitly. When unavailable, `extract_text_from_pdf` raises `ImportError` which is caught by the processor.  
**Gap:** No pre-flight check runs before the batch starts, so the error appears per-file rather than once up front (BUG-008).

---

### 4. File Permission Issues

**Scenario:** Metadata registry is read-only when saving.  
**Coverage:** `save_metadata_registry()` catches `IOError` and prints an error. Not directly tested via a real permission change (requires root or specific OS setup).  
**Recommendation:** Add a write-permission check before opening the registry for writing.

---

### 5. Metadata Registry Corruption

**Scenario:** articles_metadata.json contains invalid JSON.  
**Tests:**  
- `TestArticleProcessor::test_load_corrupted_registry` — processor falls back to empty dict  
- `TestQueryMetadata::test_load_registry_corrupted` — query tool returns empty dict  
- `TestCLILayer::test_get_stats_with_corrupted_registry` — dashboard shows 0s  
**Result:** All three layers handle corruption gracefully without crashing.

---

### 6. Filename Sanitization Edge Cases

**Tests in `TestSanitizeFilename`:**
- All reserved characters: `<>:"/\|?*` — all stripped
- Unicode titles (Über, é, ç) — pass through
- Emoji characters — pass through (may cause issues on some filesystems)
- Null bytes (`\x00`) — pass through (can corrupt filesystem entries on some OS)
- Very long titles (1000 chars) — not truncated (BUG-004 — no length cap)
- Trailing dots and leading dots — stripped correctly
- All-invalid-char strings — return empty string (safe)

---

### 7. Publication Detection Edge Cases

**Tests in `TestExtractPublication`:**
- All 6 known publications detected
- Case-insensitive matching works
- Text beyond 1500 chars is ignored (position cutoff test)
- Unknown publication returns `None` correctly

**Known gap:** The detection is a first-match-wins scan. If both "mckinsey" and "harvard business review" appear in the same text, ArticleForge wins because it appears earlier in the dict definition order. The dict iteration order in Python 3.7+ is insertion order — this is stable but fragile.

---

### 8. Character Encoding Issues

**Tests in `TestEncodingEdgeCases`:**
- UTF-8 markdown write/read round-trip with accented chars
- Non-ASCII keywords don't crash extraction
- Curly quotes in filenames sanitized without crash
- JSON registry round-trip preserves Unicode (using `ensure_ascii=False`)

**Gap:** The CSV export does not specify an encoding for the DictWriter. It uses `encoding='utf-8'` in `open()`, but some Windows CSV tools default to cp1252. Authors with accented names (e.g., "André") may display incorrectly in Excel on Windows. Adding a UTF-8 BOM would fix this.

---

### 9. Very Large Batches

**Test:** `TestEdgeCases::test_large_batch_processing_stats` — stats dict handles large numbers (500 articles).  
**Test:** `TestExtractKeywords::test_very_long_text` — 100,000-char text processed without crash.  
**Gap:** No test for processing 100+ PDFs sequentially. Memory accumulation in `self.metadata['articles']` is unbounded; for very large libraries (10,000+ articles), loading the entire JSON into memory on every run may become slow.

---

### 10. Concurrent Access

**Coverage:** None (BUG-009). No file locking is implemented. This is documented as a known issue.  
**Test recommendation:** Use `multiprocessing` to spawn two simultaneous writer processes and verify that the resulting registry has entries from both (requires file locking to pass).

---

### 11. Malformed JSON / CSV

**Scenario:** `manual_metadata_overrides.json` is malformed.  
**Test:** `TestArticleProcessor::test_load_manual_overrides_corrupted` — returns `{}` safely.  

**Scenario:** YAML frontmatter cannot be split on `---`.  
**Tests:**  
- `TestArticleProcessor::test_rebuild_registry_invalid_frontmatter` — no crash  
- `TestArticleProcessor::test_rebuild_registry_partial_frontmatter` — no crash

---

### 12. Missing Override Entries

**Scenario:** A PDF with no extractable title and no matching override entry.  
**Coverage:** `process_pdf()` returns `None` and increments `failed` when title is None and no override exists. This is tested via the stats tracking tests.

---

### 13. Keyword Extraction Edge Cases

**Tests:**
- Empty string input → `[]`
- `None` input → `[]`
- Only stopwords → `[]` (or near-empty)
- Only 3-letter words → `[]` (filtered by length)
- Only digits → `[]` (filtered by `isdigit()`)
- Hyphenated words (`state-of-the-art`) — treated as single token, leading/trailing hyphens stripped
- Unicode words — not crashed by non-ASCII
- `num_keywords=0` → `[]`

---

### 14. YAML Injection / Title Injection

**Test:** `TestEdgeCases::test_title_injection_in_yaml` — title containing `---` does not break the document structure (though it may produce technically invalid YAML — see BUG-002).  
**Test:** `TestCreateMarkdownContent::test_title_with_special_yaml_chars` — title with colon does not crash, but the resulting YAML is invalid.

---

### 15. Leap Year Date Handling

**Tests:**
- `test_extract_date_feb_29_leap_year` — February 29, 2024 (valid leap year) → `"2024-02-29"` ✓  
- `test_extract_date_feb_29_non_leap_year` — February 29, 2023 (invalid) → `None` ✓  
The `ValueError` from `strptime` is caught by the `except (ValueError, AttributeError): continue` in `extract_date()`.

---

## Continuous Integration Recommendations

Add this to your CI pipeline (GitHub Actions, etc.):

```yaml
- name: Run test suite
  run: |
    pip install pytest pdfplumber PyPDF2 Pillow
    pytest test_suite.py -v --tb=short --junit-xml=test-results.xml

- name: Check for critical failures
  run: |
    pytest test_suite.py -v -k "BUG or critical" --tb=short
```

## Regression Test Protocol

After any code change to `utils.py`, `process_articles.py`, or `config.py`:

1. Run the full suite: `pytest test_suite.py -v`
2. All 175 tests must pass (after BUG-001 is fixed)
3. Pay special attention to:
   - `TestSanitizeFilename` after any filename changes
   - `TestCreateMarkdownContent` after YAML format changes
   - `TestRegressionCases` after any changes to registry schema
   - `TestArticleProcessor::test_load_corrupted_registry` after any registry loading changes
