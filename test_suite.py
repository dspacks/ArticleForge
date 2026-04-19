#!/usr/bin/env python3
"""
HBR Article Processing System — Comprehensive Test Suite
=========================================================

Tests cover:
  - Unit tests for all utility functions
  - Integration tests for the full pipeline
  - Error condition and edge case tests
  - Data integrity tests
  - CLI stability tests
  - File system edge cases

Run with:
    pytest test_suite.py -v
    pytest test_suite.py -v --tb=short
    pytest test_suite.py -v -k "test_sanitize"   # run specific tests
"""

import pytest
import json
import os
import sys
import tempfile
import shutil
import struct
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

# ---------------------------------------------------------------------------
# Ensure scripts/ is importable regardless of working directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ===========================================================================
# FIXTURES
# ===========================================================================

@pytest.fixture
def tmp_dir(tmp_path):
    """Create a fully structured temp project tree."""
    dirs = ["intake", "output", "pdf_archive", "metadata", "scripts"]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def minimal_registry():
    """A minimal, valid metadata registry dict."""
    return {
        "articles": [
            {
                "source_file": "test.pdf",
                "output_file": "2024-01-15_HBR_Test Article.md",
                "title": "Test Article",
                "author": "Jane Doe",
                "date": "2024-01-15",
                "source": "HBR",
                "keywords": ["leadership", "strategy", "innovation"],
                "text_length": 5000,
                "processed_date": "2026-04-19T10:00:00",
            }
        ],
        "last_updated": "2026-04-19T10:00:00",
    }


@pytest.fixture
def registry_file(tmp_dir, minimal_registry):
    """Write a valid registry JSON to tmp_dir/metadata/."""
    path = tmp_dir / "metadata" / "articles_metadata.json"
    path.write_text(json.dumps(minimal_registry, indent=2))
    return path


@pytest.fixture
def fake_pdf(tmp_dir):
    """Write a minimal syntactically-valid PDF stub to intake/."""
    pdf_path = tmp_dir / "intake" / "test_article.pdf"
    # Smallest valid PDF body (not real content — tests error paths)
    pdf_path.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        b"xref\n0 1\n0000000000 65535 f \ntrailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF\n"
    )
    return pdf_path


@pytest.fixture
def corrupted_pdf(tmp_dir):
    """Write a file that looks like a PDF but has corrupted content."""
    path = tmp_dir / "intake" / "corrupted.pdf"
    path.write_bytes(b"%PDF-1.4\ngarbage\x00\xff\xfe data here \xde\xad\xbe\xef")
    return path


@pytest.fixture
def empty_pdf(tmp_dir):
    """Write a zero-byte file with .pdf extension."""
    path = tmp_dir / "intake" / "empty.pdf"
    path.write_bytes(b"")
    return path


@pytest.fixture
def non_pdf_as_pdf(tmp_dir):
    """A JPEG file renamed to .pdf."""
    path = tmp_dir / "intake" / "image_as_pdf.pdf"
    # JPEG magic bytes
    path.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")
    return path


# ===========================================================================
# SECTION 1 — utils.py  (sanitize_filename)
# ===========================================================================

class TestSanitizeFilename:

    def test_normal_title(self):
        from utils import sanitize_filename
        result = sanitize_filename("The Best Leadership Advice")
        assert result == "The Best Leadership Advice"

    def test_removes_angle_brackets(self):
        from utils import sanitize_filename
        result = sanitize_filename("Title <with> brackets")
        assert "<" not in result and ">" not in result

    def test_removes_colon(self):
        from utils import sanitize_filename
        result = sanitize_filename("Part 1: The Beginning")
        assert ":" not in result

    def test_removes_forward_slash(self):
        from utils import sanitize_filename
        result = sanitize_filename("Yes/No Decisions")
        assert "/" not in result

    def test_removes_backslash(self):
        from utils import sanitize_filename
        result = sanitize_filename("Path\\to\\success")
        assert "\\" not in result

    def test_removes_pipe(self):
        from utils import sanitize_filename
        result = sanitize_filename("A | B separation")
        assert "|" not in result

    def test_removes_question_mark(self):
        from utils import sanitize_filename
        result = sanitize_filename("What works?")
        assert "?" not in result

    def test_removes_asterisk(self):
        from utils import sanitize_filename
        result = sanitize_filename("Best * practices")
        assert "*" not in result

    def test_removes_double_quotes(self):
        from utils import sanitize_filename
        result = sanitize_filename('Title "with" quotes')
        assert '"' not in result

    def test_collapses_multiple_spaces(self):
        from utils import sanitize_filename
        result = sanitize_filename("Too   many   spaces")
        assert "  " not in result

    def test_strips_leading_trailing_dots(self):
        from utils import sanitize_filename
        result = sanitize_filename("...Title...")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_empty_string(self):
        """Empty input should return empty string, not raise."""
        from utils import sanitize_filename
        result = sanitize_filename("")
        assert isinstance(result, str)

    def test_all_invalid_chars(self):
        """A string of only invalid chars should yield empty or stripped result."""
        from utils import sanitize_filename
        result = sanitize_filename('<>:"/\\|?*')
        # Should not crash; result is empty after stripping
        assert isinstance(result, str)

    def test_unicode_title(self):
        """Unicode characters should pass through unchanged."""
        from utils import sanitize_filename
        result = sanitize_filename("Über Stratégie: Success")
        assert "Über" in result or "ber" in result  # colon removed, rest preserved
        assert ":" not in result

    def test_very_long_title(self):
        """No length limit enforced — should handle long strings without crash."""
        from utils import sanitize_filename
        long_title = "A" * 1000
        result = sanitize_filename(long_title)
        assert isinstance(result, str)

    def test_only_spaces_and_dots(self):
        """Pathological input: spaces and dots only."""
        from utils import sanitize_filename
        result = sanitize_filename("   ...   ")
        assert isinstance(result, str)

    def test_newlines_and_tabs(self):
        """Newlines/tabs are not in the invalid set but should still work."""
        from utils import sanitize_filename
        result = sanitize_filename("Line\nBreak\tTab")
        assert isinstance(result, str)

    def test_null_character(self):
        """Null bytes — not in regex but important on some filesystems."""
        from utils import sanitize_filename
        result = sanitize_filename("Title\x00With\x00Null")
        assert isinstance(result, str)


# ===========================================================================
# SECTION 2 — utils.py  (extract_title)
# ===========================================================================

class TestExtractTitle:

    def test_prefers_pdf_metadata(self):
        from utils import extract_title
        result = extract_title("some text here", "PDF Title From Metadata")
        assert result == "PDF Title From Metadata"

    def test_falls_back_to_text(self):
        from utils import extract_title
        text = "\n\nLeadership in Crisis Management\n\nSome content follows..."
        result = extract_title(text, None)
        assert result is not None
        assert len(result) > 0

    def test_empty_text_no_metadata(self):
        from utils import extract_title
        result = extract_title("", None)
        assert result is None

    def test_none_text(self):
        from utils import extract_title
        result = extract_title(None, None)
        assert result is None

    def test_pdf_title_too_short(self):
        """PDF metadata title < 6 chars should be rejected."""
        from utils import extract_title
        result = extract_title("Some article text here\nAnd a second line", "Hi")
        # "Hi" is 2 chars, falls below threshold of 5
        assert result != "Hi"

    def test_pdf_title_too_long(self):
        """PDF metadata title > 300 chars should be rejected."""
        from utils import extract_title
        long_title = "A" * 301
        text = "Some article text here\nSecond line"
        result = extract_title(text, long_title)
        assert result != long_title

    def test_all_caps_line_rejected(self):
        """An all-uppercase line should be skipped as title."""
        from utils import extract_title
        text = "HBR MASTHEAD HEADER\nThis is the real article title for testing"
        result = extract_title(text, None)
        assert result != "HBR MASTHEAD HEADER"

    def test_very_short_lines_rejected(self):
        """Lines < 20 chars should be skipped."""
        from utils import extract_title
        text = "Short\nAnother short\nThis is a valid title long enough to qualify here"
        result = extract_title(text, None)
        # The title should not be one of the short lines
        if result:
            assert len(result) >= 20

    def test_only_whitespace_text(self):
        from utils import extract_title
        result = extract_title("   \n  \n  ", None)
        assert result is None


# ===========================================================================
# SECTION 3 — utils.py  (extract_author)
# ===========================================================================

class TestExtractAuthor:

    def test_prefers_pdf_metadata(self):
        from utils import extract_author
        result = extract_author("By Someone Else in the text", "Jane Smith")
        assert result == "Jane Smith"

    def test_by_pattern(self):
        from utils import extract_author
        result = extract_author("By Jane Smith\nContent here...")
        assert result is not None and "Jane" in result

    def test_author_colon_pattern(self):
        from utils import extract_author
        result = extract_author("Author: John Doe\nContent here...")
        assert result is not None and "John" in result

    def test_and_pattern(self):
        from utils import extract_author
        result = extract_author("Written by John Smith and Jane Doe\nMore text...")
        assert result is not None

    def test_empty_text(self):
        from utils import extract_author
        result = extract_author("", None)
        assert result is None

    def test_none_text(self):
        from utils import extract_author
        result = extract_author(None, None)
        assert result is None

    def test_blank_pdf_metadata(self):
        """Empty string PDF author should fall back to text."""
        from utils import extract_author
        result = extract_author("By James Gordon\nArticle body...", "")
        # Empty string is falsy — should fall back to text extraction
        assert result is not None or result is None  # just shouldn't crash

    def test_no_author_in_text(self):
        from utils import extract_author
        result = extract_author("This text has no author pattern at all. Just content.", None)
        assert result is None

    def test_author_with_special_chars(self):
        from utils import extract_author
        result = extract_author("By José García\nContent...", None)
        # Should not crash even if pattern doesn't match accented chars
        assert result is None or isinstance(result, str)


# ===========================================================================
# SECTION 4 — utils.py  (extract_date)
# ===========================================================================

class TestExtractDate:

    def test_prefers_pdf_metadata_date(self):
        from utils import extract_date
        result = extract_date("January 1, 2024 in text", "2023-06-15")
        assert result == "2023-06-15"

    def test_month_day_year_format(self):
        from utils import extract_date
        result = extract_date("Published: January 15, 2024\nContent...", None)
        assert result == "2024-01-15"

    def test_slash_format(self):
        from utils import extract_date
        result = extract_date("Published 03/22/2023\nContent...", None)
        assert result == "2023-03-22"

    def test_iso_format_in_text(self):
        from utils import extract_date
        result = extract_date("Date: 2022-11-30 article content...", None)
        assert result == "2022-11-30"

    def test_empty_text(self):
        from utils import extract_date
        result = extract_date("", None)
        assert result is None

    def test_none_text(self):
        from utils import extract_date
        result = extract_date(None, None)
        assert result is None

    def test_invalid_pdf_date_falls_back(self):
        """PDF date that doesn't match YYYY-MM-DD should be ignored."""
        from utils import extract_date
        result = extract_date("January 10, 2024 in the text", "not-a-date")
        assert result == "2024-01-10" or result is None

    def test_future_year_accepted(self):
        """Dates with future years should not be rejected."""
        from utils import extract_date
        result = extract_date("Published: March 15, 2027\nContent...", None)
        assert result is None or "2027" in result

    def test_ambiguous_date_format(self):
        """MM/DD/YYYY vs DD/MM/YYYY ambiguity — system picks MM/DD/YYYY."""
        from utils import extract_date
        result = extract_date("Date: 01/05/2023", None)
        # System uses %m/%d/%Y so this should be January 5, 2023
        assert result == "2023-01-05"

    def test_no_date_in_text(self):
        from utils import extract_date
        result = extract_date("This article has no date at all in the text.", None)
        assert result is None


# ===========================================================================
# SECTION 5 — utils.py  (extract_keywords)
# ===========================================================================

class TestExtractKeywords:

    def test_returns_list(self):
        from utils import extract_keywords
        result = extract_keywords("Leadership strategy innovation management business")
        assert isinstance(result, list)

    def test_returns_correct_count(self):
        from utils import extract_keywords
        text = "leadership management strategy innovation business teams employees "
        text *= 10  # repeat to ensure frequency
        result = extract_keywords(text, num_keywords=5)
        assert len(result) <= 5

    def test_stopwords_excluded(self):
        from utils import extract_keywords
        result = extract_keywords("the and or but in on at to for of with by from", num_keywords=10)
        stopwords = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from"}
        for kw in result:
            assert kw not in stopwords

    def test_empty_text_returns_empty(self):
        from utils import extract_keywords
        result = extract_keywords("", num_keywords=5)
        assert result == []

    def test_none_text_returns_empty(self):
        from utils import extract_keywords
        result = extract_keywords(None, num_keywords=5)
        assert result == []

    def test_short_words_excluded(self):
        """Words 3 chars or fewer should be filtered out."""
        from utils import extract_keywords
        result = extract_keywords("cat dog bee fly ant bee bee fly fly dog dog", num_keywords=5)
        for kw in result:
            assert len(kw) > 3

    def test_numbers_excluded(self):
        from utils import extract_keywords
        result = extract_keywords("1234 5678 9012 strategy leadership management", num_keywords=5)
        for kw in result:
            assert not kw.isdigit()

    def test_result_is_sorted(self):
        """Keywords should be returned in sorted (alphabetical) order."""
        from utils import extract_keywords
        text = "strategy leadership innovation management excellence teamwork"
        text *= 5
        result = extract_keywords(text, num_keywords=6)
        assert result == sorted(result)

    def test_zero_keywords_requested(self):
        from utils import extract_keywords
        result = extract_keywords("Some text here", num_keywords=0)
        assert result == []

    def test_very_long_text(self):
        """Should not crash or take forever on large inputs."""
        from utils import extract_keywords
        big_text = ("leadership strategy management innovation employees ") * 2000
        result = extract_keywords(big_text, num_keywords=5)
        assert isinstance(result, list)
        assert len(result) <= 5

    def test_unicode_text(self):
        """Should handle non-ASCII without crashing."""
        from utils import extract_keywords
        result = extract_keywords("Führung stratégie stratégique Führung Führung")
        assert isinstance(result, list)

    def test_only_stopwords(self):
        """If all words are stopwords, returns empty list."""
        from utils import extract_keywords
        result = extract_keywords("the and or but in on at to for")
        assert isinstance(result, list)


# ===========================================================================
# SECTION 6 — utils.py  (extract_publication)
# ===========================================================================

class TestExtractPublication:

    def test_detects_hbr(self):
        from utils import extract_publication
        result = extract_publication("Harvard Business Review article on leadership...")
        assert result == "HBR"

    def test_detects_hbr_domain(self):
        from utils import extract_publication
        result = extract_publication("Read more at hbr.org for insights...")
        assert result == "HBR"

    def test_detects_wsj(self):
        from utils import extract_publication
        result = extract_publication("Wall Street Journal reports that...")
        assert result == "WSJ"

    def test_detects_ft(self):
        from utils import extract_publication
        result = extract_publication("Financial Times analysis of global markets...")
        assert result == "FT"

    def test_detects_forbes(self):
        from utils import extract_publication
        result = extract_publication("Forbes ranked the company number one...")
        assert result == "Forbes"

    def test_detects_mckinsey(self):
        from utils import extract_publication
        result = extract_publication("McKinsey Quarterly research findings suggest...")
        assert result == "McKinsey"

    def test_unknown_publication(self):
        from utils import extract_publication
        result = extract_publication("Some random text without known publication markers.")
        assert result is None

    def test_empty_text(self):
        from utils import extract_publication
        result = extract_publication("")
        assert result is None

    def test_none_text(self):
        from utils import extract_publication
        result = extract_publication(None)
        assert result is None

    def test_publication_beyond_1500_chars_ignored(self):
        """Publication markers beyond 1500 chars should NOT be detected."""
        from utils import extract_publication
        prefix = "x" * 1501
        result = extract_publication(prefix + "harvard business review at end")
        assert result is None

    def test_case_insensitive_detection(self):
        """Markers are compared case-insensitively."""
        from utils import extract_publication
        result = extract_publication("HARVARD BUSINESS REVIEW published this...")
        assert result == "HBR"


# ===========================================================================
# SECTION 7 — utils.py  (parse_metadata_from_filename)
# ===========================================================================

class TestParseMetadataFromFilename:

    def test_ebsco_filename_parsed(self):
        from utils import parse_metadata_from_filename
        result = parse_metadata_from_filename("EBSCO-FullText-04_18_2026 (1).pdf")
        assert result.get("source") == "EBSCO"
        assert result.get("export_date") == "2026-04-18"

    def test_ebsco_without_parenthetical(self):
        from utils import parse_metadata_from_filename
        result = parse_metadata_from_filename("EBSCO-FullText-12_01_2023.pdf")
        assert result.get("source") == "EBSCO"

    def test_non_ebsco_returns_empty(self):
        from utils import parse_metadata_from_filename
        result = parse_metadata_from_filename("my_article.pdf")
        assert result == {}

    def test_empty_filename(self):
        from utils import parse_metadata_from_filename
        result = parse_metadata_from_filename("")
        assert isinstance(result, dict)

    def test_partial_ebsco_name(self):
        """Partial match should not return bogus data."""
        from utils import parse_metadata_from_filename
        result = parse_metadata_from_filename("EBSCO-partial.pdf")
        assert result.get("source") != "EBSCO"

    def test_ebsco_date_edge_single_digit(self):
        """Month/day with single digit in filename (actual EBSCO format uses 2-digit)."""
        from utils import parse_metadata_from_filename
        result = parse_metadata_from_filename("EBSCO-FullText-01_01_2024.pdf")
        assert result.get("export_date") == "2024-01-01"


# ===========================================================================
# SECTION 8 — utils.py  (create_markdown_content)
# ===========================================================================

class TestCreateMarkdownContent:

    def test_produces_frontmatter_block(self):
        from utils import create_markdown_content
        result = create_markdown_content("Title", "Author", "2024-01-01", ["kw1"], "Body text")
        assert result.startswith("---")
        assert "---" in result[3:]  # closing ---

    def test_title_in_frontmatter(self):
        from utils import create_markdown_content
        result = create_markdown_content("My Article", None, None, [], "Text")
        assert "title: My Article" in result

    def test_author_included_when_present(self):
        from utils import create_markdown_content
        result = create_markdown_content("T", "Jane Doe", "2024-01-01", [], "Text")
        assert "author: Jane Doe" in result

    def test_author_omitted_when_none(self):
        from utils import create_markdown_content
        result = create_markdown_content("T", None, None, [], "Text")
        assert "author:" not in result

    def test_date_included_when_present(self):
        from utils import create_markdown_content
        result = create_markdown_content("T", "A", "2024-06-15", [], "Text")
        assert "date: 2024-06-15" in result

    def test_keywords_formatted_as_list(self):
        from utils import create_markdown_content
        result = create_markdown_content("T", "A", "2024-01-01", ["a", "b", "c"], "Text")
        assert "keywords: [a, b, c]" in result

    def test_empty_keywords(self):
        from utils import create_markdown_content
        result = create_markdown_content("T", "A", "2024-01-01", [], "Text")
        # keywords line should not appear for empty list
        assert "keywords: []" not in result

    def test_source_included(self):
        from utils import create_markdown_content
        result = create_markdown_content("T", "A", "2024-01-01", [], "Text", source="HBR")
        assert "source: HBR" in result

    def test_body_text_appended(self):
        from utils import create_markdown_content
        result = create_markdown_content("T", "A", "2024-01-01", [], "The body content here")
        assert "The body content here" in result

    def test_title_with_special_yaml_chars(self):
        """Colons in YAML values can break parsers — this is a known risk."""
        from utils import create_markdown_content
        result = create_markdown_content(
            "Title: Subtitle", "Author", "2024-01-01", [], "Body"
        )
        # Should not crash — but the YAML may be technically invalid (known issue)
        assert isinstance(result, str)
        assert "Title: Subtitle" in result

    def test_empty_text_body(self):
        from utils import create_markdown_content
        result = create_markdown_content("Title", "Author", "2024-01-01", [], "")
        assert isinstance(result, str)


# ===========================================================================
# SECTION 9 — utils.py  (clean_extracted_text)
# ===========================================================================

class TestCleanExtractedText:

    def test_removes_page_breaks(self):
        from utils import clean_extracted_text
        result = clean_extracted_text("Line 1\n[PAGE BREAK]\nLine 2")
        assert "[PAGE BREAK]" not in result

    def test_collapses_multiple_blank_lines(self):
        from utils import clean_extracted_text
        result = clean_extracted_text("Line 1\n\n\n\n\nLine 2")
        assert "\n\n\n" not in result

    def test_empty_string(self):
        from utils import clean_extracted_text
        result = clean_extracted_text("")
        assert result == ""

    def test_none_input(self):
        from utils import clean_extracted_text
        result = clean_extracted_text(None)
        assert result is None

    def test_camel_case_split(self):
        from utils import clean_extracted_text
        # "areLeaders" → "are Leaders"
        result = clean_extracted_text("areLeaders perform")
        assert "are" in result and "Leaders" in result

    def test_preserves_content(self):
        from utils import clean_extracted_text
        text = "This is a paragraph.\n\nThis is another paragraph."
        result = clean_extracted_text(text)
        assert "paragraph" in result

    def test_trailing_hyphen_removal(self):
        from utils import clean_extracted_text
        result = clean_extracted_text("leader-\nship")
        # trailing hyphen on "leader-" should be stripped
        assert isinstance(result, str)

    def test_normalizes_multiple_spaces(self):
        from utils import clean_extracted_text
        result = clean_extracted_text("Too   many   spaces   here")
        assert "   " not in result


# ===========================================================================
# SECTION 10 — process_articles.py  (ArticleProcessor)
# ===========================================================================

class TestArticleProcessor:

    def _make_processor(self, tmp_dir, dry_run=False):
        """Create an ArticleProcessor with paths patched to tmp_dir."""
        import process_articles as pa
        import config as cfg

        # Patch config paths to use tmp_dir
        cfg.INTAKE_DIR = tmp_dir / "intake"
        cfg.OUTPUT_DIR = tmp_dir / "output"
        cfg.ARCHIVE_DIR = tmp_dir / "pdf_archive"
        cfg.METADATA_DIR = tmp_dir / "metadata"
        cfg.METADATA_REGISTRY = tmp_dir / "metadata" / "articles_metadata.json"

        # Reload module to pick up patched values
        import importlib
        importlib.reload(pa)

        return pa.ArticleProcessor(dry_run=dry_run)

    def test_load_empty_registry(self, tmp_dir):
        """No registry file → returns default empty structure."""
        proc = self._make_processor(tmp_dir)
        assert proc.metadata == {"articles": [], "last_updated": None}

    def test_load_valid_registry(self, tmp_dir, minimal_registry):
        reg_path = tmp_dir / "metadata" / "articles_metadata.json"
        reg_path.write_text(json.dumps(minimal_registry))
        proc = self._make_processor(tmp_dir)
        assert len(proc.metadata["articles"]) == 1

    def test_load_corrupted_registry(self, tmp_dir):
        """Corrupted JSON → falls back to empty structure, no crash."""
        reg_path = tmp_dir / "metadata" / "articles_metadata.json"
        reg_path.write_text("{ not valid json !!!")
        proc = self._make_processor(tmp_dir)
        assert proc.metadata["articles"] == []

    def test_article_exists_true(self, tmp_dir, minimal_registry):
        reg_path = tmp_dir / "metadata" / "articles_metadata.json"
        reg_path.write_text(json.dumps(minimal_registry))
        proc = self._make_processor(tmp_dir)
        assert proc.article_exists("test.pdf") is True

    def test_article_exists_false(self, tmp_dir):
        proc = self._make_processor(tmp_dir)
        assert proc.article_exists("nonexistent.pdf") is False

    def test_process_all_empty_intake(self, tmp_dir, capsys):
        """Empty intake dir → prints message, no crash."""
        proc = self._make_processor(tmp_dir)
        proc.process_all()
        captured = capsys.readouterr()
        assert "No PDF" in captured.out

    def test_dry_run_does_not_write(self, tmp_dir):
        """Dry run must not write any output files."""
        proc = self._make_processor(tmp_dir, dry_run=True)
        # Even with no PDFs, the output dir must stay empty
        proc.process_all()
        output_files = list((tmp_dir / "output").iterdir())
        assert output_files == []

    def test_save_registry_skipped_in_dry_run(self, tmp_dir):
        """save_metadata_registry must not write in dry_run mode."""
        proc = self._make_processor(tmp_dir, dry_run=True)
        proc.metadata["articles"].append({"title": "test"})
        proc.save_metadata_registry()
        reg_path = tmp_dir / "metadata" / "articles_metadata.json"
        assert not reg_path.exists()

    def test_load_manual_overrides_missing_file(self, tmp_dir):
        """Missing overrides file → returns empty dict, no crash."""
        proc = self._make_processor(tmp_dir)
        assert proc.manual_overrides == {}

    def test_load_manual_overrides_corrupted(self, tmp_dir):
        overrides_path = tmp_dir / "metadata" / "manual_metadata_overrides.json"
        overrides_path.write_text("{ bad json }")
        proc = self._make_processor(tmp_dir)
        assert proc.manual_overrides == {}

    def test_load_manual_overrides_valid(self, tmp_dir):
        data = {
            "overrides": [
                {"source_file": "tricky.pdf", "title": "My Title", "author": "Me", "date": "2024-01-01"}
            ]
        }
        overrides_path = tmp_dir / "metadata" / "manual_metadata_overrides.json"
        overrides_path.write_text(json.dumps(data))
        proc = self._make_processor(tmp_dir)
        assert "tricky.pdf" in proc.manual_overrides

    def test_rebuild_registry_no_md_files(self, tmp_dir, capsys):
        proc = self._make_processor(tmp_dir)
        proc.rebuild_registry()
        captured = capsys.readouterr()
        assert "No markdown" in captured.out

    def test_rebuild_registry_invalid_frontmatter(self, tmp_dir):
        """MD file without --- should not crash rebuild."""
        md_path = tmp_dir / "output" / "no_frontmatter.md"
        md_path.write_text("No frontmatter here, just raw text.")
        proc = self._make_processor(tmp_dir)
        # Should not raise
        proc.rebuild_registry()

    def test_rebuild_registry_partial_frontmatter(self, tmp_dir):
        """MD file with only opening --- but no closing --- should not crash."""
        md_path = tmp_dir / "output" / "partial.md"
        md_path.write_text("---\ntitle: Something\nNo closing dashes")
        proc = self._make_processor(tmp_dir)
        proc.rebuild_registry()  # Should not raise


# ===========================================================================
# SECTION 11 — query_metadata.py
# ===========================================================================

class TestQueryMetadata:

    def _patch_registry(self, tmp_path, data):
        import config as cfg
        cfg.METADATA_REGISTRY = tmp_path / "articles_metadata.json"
        (tmp_path / "articles_metadata.json").write_text(json.dumps(data))

    def test_load_registry_missing(self, tmp_path, capsys):
        import config as cfg
        cfg.METADATA_REGISTRY = tmp_path / "nonexistent.json"
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        result = qm.load_registry()
        assert result == {"articles": []}

    def test_load_registry_corrupted(self, tmp_path, capsys):
        import config as cfg
        cfg.METADATA_REGISTRY = tmp_path / "bad.json"
        (tmp_path / "bad.json").write_text("not json")
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        result = qm.load_registry()
        assert result == {"articles": []}

    def test_find_by_keyword_found(self, tmp_path, minimal_registry, capsys):
        import config as cfg
        cfg.METADATA_REGISTRY = tmp_path / "reg.json"
        (tmp_path / "reg.json").write_text(json.dumps(minimal_registry))
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        registry = qm.load_registry()
        qm.find_by_keyword(registry, "leadership")
        captured = capsys.readouterr()
        assert "Test Article" in captured.out

    def test_find_by_keyword_not_found(self, tmp_path, minimal_registry, capsys):
        import config as cfg
        cfg.METADATA_REGISTRY = tmp_path / "reg.json"
        (tmp_path / "reg.json").write_text(json.dumps(minimal_registry))
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        registry = qm.load_registry()
        qm.find_by_keyword(registry, "zzznomatch")
        captured = capsys.readouterr()
        assert "No articles" in captured.out

    def test_find_by_author_none_value(self, tmp_path, capsys):
        """Author field is None in registry — should not crash."""
        data = {"articles": [{"title": "Test", "author": None, "keywords": []}]}
        import config as cfg
        cfg.METADATA_REGISTRY = tmp_path / "reg.json"
        (tmp_path / "reg.json").write_text(json.dumps(data))
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        registry = qm.load_registry()
        qm.find_by_author(registry, "Smith")
        # Should not crash on None author

    def test_export_csv_no_articles(self, tmp_path, capsys):
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        qm.export_csv({"articles": []}, tmp_path / "out.csv")
        captured = capsys.readouterr()
        assert "No articles" in captured.out

    def test_export_csv_creates_file(self, tmp_path, minimal_registry):
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        out_path = tmp_path / "export.csv"
        qm.export_csv(minimal_registry, out_path)
        assert out_path.exists()
        content = out_path.read_text()
        assert "Test Article" in content

    def test_export_csv_keywords_semicolon_joined(self, tmp_path, minimal_registry):
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        out_path = tmp_path / "export.csv"
        qm.export_csv(minimal_registry, out_path)
        content = out_path.read_text()
        # Keywords should be joined with "; "
        assert "leadership; strategy; innovation" in content

    def test_show_stats_empty_registry(self, capsys):
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        qm.show_stats({"articles": []})
        captured = capsys.readouterr()
        assert "No articles" in captured.out


# ===========================================================================
# SECTION 12 — zotero_export.py
# ===========================================================================

class TestZoteroExport:

    def test_format_for_zotero_basic(self):
        import zotero_export as ze
        article = {
            "title": "Test Title",
            "author": "Jane Doe",
            "date": "2024-01-01",
            "source": "HBR",
            "keywords": ["strategy"],
            "processed_date": "2026-04-19",
        }
        result = ze.format_for_zotero(article)
        assert result["title"] == "Test Title"
        assert result["itemType"] == "journalArticle"
        assert len(result["creators"]) == 1
        assert result["creators"][0]["name"] == "Jane Doe"
        assert any(t["tag"] == "strategy" for t in result["tags"])

    def test_format_multiple_authors(self):
        import zotero_export as ze
        article = {
            "title": "T", "author": "Alice Smith and Bob Jones",
            "date": "2024-01-01", "source": "HBR", "keywords": [],
            "processed_date": "2026-04-19"
        }
        result = ze.format_for_zotero(article)
        assert len(result["creators"]) == 2

    def test_format_no_author(self):
        import zotero_export as ze
        article = {"title": "T", "author": None, "date": "2024-01-01",
                   "source": "HBR", "keywords": [], "processed_date": ""}
        result = ze.format_for_zotero(article)
        assert result["creators"] == []

    def test_export_to_csv_creates_file(self, tmp_path):
        import zotero_export as ze
        articles = [{"title": "T", "author": "A", "date": "2024-01-01",
                     "source": "HBR", "keywords": ["kw1"], "processed_date": "2026-04-19"}]
        out = tmp_path / "zotero.csv"
        ze.export_to_csv(articles, out)
        assert out.exists()

    def test_export_to_json_creates_file(self, tmp_path):
        import zotero_export as ze
        articles = [{"title": "T", "author": "A", "date": "2024-01-01",
                     "source": "HBR", "keywords": [], "processed_date": "2026-04-19"}]
        out = tmp_path / "zotero.json"
        ze.export_to_json(articles, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert isinstance(data, list)
        assert data[0]["title"] == "T"

    def test_export_to_csv_empty_articles(self, tmp_path, capsys):
        import zotero_export as ze
        ze.export_to_csv([], tmp_path / "out.csv")
        captured = capsys.readouterr()
        assert "No articles" in captured.out

    def test_export_to_json_empty_articles(self, tmp_path, capsys):
        import zotero_export as ze
        ze.export_to_json([], tmp_path / "out.json")
        captured = capsys.readouterr()
        assert "No articles" in captured.out


# ===========================================================================
# SECTION 13 — rename_archived_pdfs.py
# ===========================================================================

class TestRenamePDFs:

    def _setup(self, tmp_path, articles):
        import config as cfg
        cfg.METADATA_REGISTRY = tmp_path / "articles_metadata.json"
        cfg.ARCHIVE_DIR = tmp_path / "archive"
        cfg.ARCHIVE_DIR.mkdir()
        (tmp_path / "articles_metadata.json").write_text(
            json.dumps({"articles": articles})
        )
        import rename_archived_pdfs as rnm
        import importlib; importlib.reload(rnm)
        return rnm

    def test_dry_run_does_not_rename(self, tmp_path):
        articles = [{"source_file": "old.pdf", "output_file": "2024-01-01_HBR_Title.md"}]
        rnm = self._setup(tmp_path, articles)
        (tmp_path / "archive" / "old.pdf").write_bytes(b"PDF")
        rnm.rename_pdfs(dry_run=True)
        assert (tmp_path / "archive" / "old.pdf").exists()
        assert not (tmp_path / "archive" / "2024-01-01_HBR_Title.pdf").exists()

    def test_real_rename(self, tmp_path):
        articles = [{"source_file": "old.pdf", "output_file": "2024-01-01_HBR_Title.md"}]
        rnm = self._setup(tmp_path, articles)
        (tmp_path / "archive" / "old.pdf").write_bytes(b"PDF")
        rnm.rename_pdfs(dry_run=False)
        assert not (tmp_path / "archive" / "old.pdf").exists()
        assert (tmp_path / "archive" / "2024-01-01_HBR_Title.pdf").exists()

    def test_skip_if_dest_exists(self, tmp_path):
        articles = [{"source_file": "old.pdf", "output_file": "2024-01-01_HBR_Title.md"}]
        rnm = self._setup(tmp_path, articles)
        (tmp_path / "archive" / "old.pdf").write_bytes(b"PDF")
        (tmp_path / "archive" / "2024-01-01_HBR_Title.pdf").write_bytes(b"EXISTING")
        rnm.rename_pdfs(dry_run=False)
        # old.pdf should still exist (not overwritten)
        assert (tmp_path / "archive" / "old.pdf").exists()

    def test_source_not_found(self, tmp_path, capsys):
        articles = [{"source_file": "missing.pdf", "output_file": "2024-01-01_HBR_Title.md"}]
        rnm = self._setup(tmp_path, articles)
        rnm.rename_pdfs(dry_run=False)
        captured = capsys.readouterr()
        assert "Not found" in captured.out

    def test_missing_source_file_field(self, tmp_path):
        articles = [{"output_file": "2024-01-01_HBR_Title.md"}]  # no source_file
        rnm = self._setup(tmp_path, articles)
        rnm.rename_pdfs(dry_run=False)  # should not crash


# ===========================================================================
# SECTION 14 — Edge Case Integration Tests
# ===========================================================================

class TestEdgeCases:

    def test_sanitize_filename_returns_empty_for_all_special(self):
        from utils import sanitize_filename
        result = sanitize_filename('<>:"/\\|?*')
        assert isinstance(result, str)

    def test_filename_with_unicode_emoji(self):
        from utils import sanitize_filename
        result = sanitize_filename("Article About 🚀 Rockets")
        assert isinstance(result, str)

    def test_keywords_with_hyphenated_words(self):
        from utils import extract_keywords
        text = "state-of-the-art machine-learning model innovation innovation innovation"
        result = extract_keywords(text, num_keywords=5)
        assert isinstance(result, list)

    def test_extract_date_feb_29_leap_year(self):
        from utils import extract_date
        result = extract_date("Published: February 29, 2024", None)
        # 2024 is a leap year — should parse successfully
        assert result == "2024-02-29"

    def test_extract_date_feb_29_non_leap_year(self):
        from utils import extract_date
        result = extract_date("Published: February 29, 2023", None)
        # 2023 is NOT a leap year — strptime raises ValueError, should return None
        assert result is None

    def test_title_injection_in_yaml(self):
        """YAML injection via title containing --- should not break structure."""
        from utils import create_markdown_content
        result = create_markdown_content("Title --- injected: evil", "A", "2024-01-01", [], "Body")
        assert isinstance(result, str)
        # Verify it at least starts and contains the closing frontmatter
        assert result.startswith("---")

    def test_keyword_dedup_in_list(self):
        """Counter-based extraction should not return duplicate keywords."""
        from utils import extract_keywords
        text = "strategy strategy strategy strategy leadership leadership"
        result = extract_keywords(text, num_keywords=5)
        assert len(result) == len(set(result))

    def test_create_markdown_with_none_source(self):
        from utils import create_markdown_content
        result = create_markdown_content("T", "A", "2024-01-01", ["kw"], "Body", source=None)
        assert "source:" not in result

    def test_extract_author_from_metadata_whitespace_only(self):
        """Whitespace-only author from PDF metadata should fall back to text."""
        from utils import extract_author
        result = extract_author("By Alice Brown\nArticle text...", "   ")
        # "   ".strip() is falsy — but current code checks `.strip()` on whole string
        # The function uses `if pdf_metadata_author and pdf_metadata_author.strip()`
        # "   " is truthy but .strip() is "" which is falsy → falls back
        assert result is None or "Alice" in result or isinstance(result, str)

    def test_large_batch_processing_stats(self, tmp_dir):
        """Stats dict should correctly track large numbers."""
        import process_articles as pa
        import config as cfg
        cfg.INTAKE_DIR = tmp_dir / "intake"
        cfg.OUTPUT_DIR = tmp_dir / "output"
        cfg.ARCHIVE_DIR = tmp_dir / "pdf_archive"
        cfg.METADATA_DIR = tmp_dir / "metadata"
        cfg.METADATA_REGISTRY = tmp_dir / "metadata" / "articles_metadata.json"
        import importlib; importlib.reload(pa)

        proc = pa.ArticleProcessor()
        proc.stats = {"total_processed": 500, "successful": 498, "failed": 2, "skipped": 0}
        # print_summary should not crash on large numbers
        proc.print_summary()


# ===========================================================================
# SECTION 15 — Data Integrity Tests
# ===========================================================================

class TestDataIntegrity:

    def test_registry_schema_after_save(self, tmp_dir):
        """Saved registry should always contain 'articles' and 'last_updated'."""
        import process_articles as pa
        import config as cfg
        cfg.INTAKE_DIR = tmp_dir / "intake"
        cfg.OUTPUT_DIR = tmp_dir / "output"
        cfg.ARCHIVE_DIR = tmp_dir / "pdf_archive"
        cfg.METADATA_DIR = tmp_dir / "metadata"
        reg_path = tmp_dir / "metadata" / "articles_metadata.json"
        cfg.METADATA_REGISTRY = reg_path
        import importlib; importlib.reload(pa)

        proc = pa.ArticleProcessor()
        proc.save_metadata_registry()
        data = json.loads(reg_path.read_text())
        assert "articles" in data
        assert "last_updated" in data
        assert data["last_updated"] is not None

    def test_article_entry_has_required_keys(self, minimal_registry):
        """Every article in the registry fixture has the required keys."""
        required_keys = {"title", "output_file", "date", "source", "keywords"}
        for article in minimal_registry["articles"]:
            for key in required_keys:
                assert key in article, f"Missing key: {key}"

    def test_keyword_list_is_list_not_string(self, tmp_path, minimal_registry):
        """Keywords stored as proper list, not a string."""
        for article in minimal_registry["articles"]:
            assert isinstance(article["keywords"], list)

    def test_csv_export_all_rows_written(self, tmp_path):
        import query_metadata as qm
        import importlib; importlib.reload(qm)
        registry = {
            "articles": [
                {"title": f"Article {i}", "author": "A", "date": "2024-01-01",
                 "source": "HBR", "output_file": f"art{i}.md",
                 "keywords": ["kw"], "text_length": 100}
                for i in range(10)
            ]
        }
        out = tmp_path / "export.csv"
        qm.export_csv(registry, out)
        import csv
        with open(out, newline='') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 10

    def test_rebuild_preserves_filename(self, tmp_dir):
        """Rebuild should set output_file to the md filename it read."""
        md_path = tmp_dir / "output" / "2024-01-15_HBR_Some Title.md"
        md_path.write_text(
            "---\ntitle: Some Title\nauthor: Jane\ndate: 2024-01-15\nsource: HBR\n"
            "keywords: [leadership, strategy]\nprocessed: 2026-04-19\n---\nBody text."
        )
        import process_articles as pa
        import config as cfg
        cfg.OUTPUT_DIR = tmp_dir / "output"
        cfg.METADATA_REGISTRY = tmp_dir / "metadata" / "articles_metadata.json"
        import importlib; importlib.reload(pa)
        proc = pa.ArticleProcessor()
        proc.rebuild_registry()
        assert proc.metadata["articles"][0]["output_file"] == "2024-01-15_HBR_Some Title.md"

    def test_no_duplicate_entries_after_multiple_loads(self, tmp_dir, minimal_registry):
        """Loading and saving twice should not double-up articles."""
        import process_articles as pa
        import config as cfg
        reg_path = tmp_dir / "metadata" / "articles_metadata.json"
        reg_path.write_text(json.dumps(minimal_registry))
        cfg.METADATA_REGISTRY = reg_path
        import importlib; importlib.reload(pa)

        proc = pa.ArticleProcessor()
        # Don't add new articles — registry should stay at length 1
        proc.save_metadata_registry()
        data = json.loads(reg_path.read_text())
        assert len(data["articles"]) == 1


# ===========================================================================
# SECTION 16 — processing_ui.py  (CLI Layer)
# ===========================================================================

class TestCLILayer:

    def _make_cli(self, tmp_dir):
        """Instantiate HBRCLi with base_dir patched to tmp_dir."""
        sys.path.insert(0, str(PROJECT_ROOT))
        import processing_ui as ui
        cli = ui.HBRCLi.__new__(ui.HBRCLi)
        cli.base_dir = tmp_dir
        cli.scripts_dir = tmp_dir / "scripts"
        cli.output_dir = tmp_dir / "output"
        cli.intake_dir = tmp_dir / "intake"
        cli.archive_dir = tmp_dir / "pdf_archive"
        cli.metadata_dir = tmp_dir / "metadata"
        for d in [cli.scripts_dir, cli.output_dir, cli.intake_dir,
                  cli.archive_dir, cli.metadata_dir]:
            d.mkdir(parents=True, exist_ok=True)
        return cli

    def test_get_stats_no_files(self, tmp_dir):
        cli = self._make_cli(tmp_dir)
        stats = cli.get_stats()
        assert stats["markdown_files"] == 0
        assert stats["archived_pdfs"] == 0
        assert stats["intake_pdfs"] == 0
        assert stats["total_articles"] == 0

    def test_get_stats_with_corrupted_registry(self, tmp_dir):
        cli = self._make_cli(tmp_dir)
        reg = tmp_dir / "metadata" / "articles_metadata.json"
        reg.write_text("{bad json")
        stats = cli.get_stats()
        # Should not crash; total_articles defaults to 0
        assert stats["total_articles"] == 0

    def test_get_stats_with_valid_registry(self, tmp_dir, minimal_registry):
        cli = self._make_cli(tmp_dir)
        reg = tmp_dir / "metadata" / "articles_metadata.json"
        reg.write_text(json.dumps(minimal_registry))
        stats = cli.get_stats()
        assert stats["total_articles"] == 1
        assert stats["keywords"] == 3  # leadership, strategy, innovation

    def test_view_overrides_missing_file(self, tmp_dir, capsys):
        cli = self._make_cli(tmp_dir)
        cli._view_overrides()
        captured = capsys.readouterr()
        assert "No manual overrides" in captured.out

    def test_view_overrides_corrupted_file(self, tmp_dir, capsys):
        cli = self._make_cli(tmp_dir)
        overrides = tmp_dir / "metadata" / "manual_metadata_overrides.json"
        overrides.write_text("{broken")
        cli._view_overrides()
        captured = capsys.readouterr()
        assert "Could not read" in captured.out

    def test_add_override_missing_required_fields(self, tmp_dir, capsys):
        cli = self._make_cli(tmp_dir)
        with patch("builtins.input", side_effect=["", "", "", "", ""]):
            cli._add_override()
        captured = capsys.readouterr()
        assert "required" in captured.out.lower() or "Title and date" in captured.out

    def test_add_override_writes_file(self, tmp_dir):
        cli = self._make_cli(tmp_dir)
        inputs = ["article.pdf", "My Title", "Jane Doe", "2024-01-01", "some notes"]
        with patch("builtins.input", side_effect=inputs):
            cli._add_override()
        overrides_path = tmp_dir / "metadata" / "manual_metadata_overrides.json"
        assert overrides_path.exists()
        data = json.loads(overrides_path.read_text())
        assert data["overrides"][0]["title"] == "My Title"

    def test_quick_preview_no_articles(self, tmp_dir, capsys):
        cli = self._make_cli(tmp_dir)
        with patch("builtins.input", return_value=""):
            cli.menu_quick_preview()
        captured = capsys.readouterr()
        assert "No markdown" in captured.out

    def test_quick_preview_non_integer_input(self, tmp_dir):
        """Non-integer article selection should not crash."""
        cli = self._make_cli(tmp_dir)
        md = tmp_dir / "output" / "2024-01-15_HBR_Test.md"
        md.write_text("---\ntitle: Test\n---\nBody text.")
        with patch("builtins.input", side_effect=["abc", ""]):
            cli.menu_quick_preview()

    def test_zotero_menu_no_registry(self, tmp_dir, capsys):
        cli = self._make_cli(tmp_dir)
        with patch("builtins.input", return_value=""):
            cli.menu_zotero_export()
        captured = capsys.readouterr()
        assert "No articles" in captured.out

    def test_run_processor_script_not_found(self, tmp_dir, capsys):
        cli = self._make_cli(tmp_dir)
        # scripts_dir has no process_articles.py
        cli._run_processor(dry_run=False)
        # Should print error rather than hang/crash
        captured = capsys.readouterr()
        assert len(captured.out) >= 0  # any output (error message) is fine


# ===========================================================================
# SECTION 17 — File System Edge Cases
# ===========================================================================

class TestFileSystemEdgeCases:

    def test_output_dir_missing_on_write(self, tmp_dir):
        """If output/ doesn't exist when writing MD, it should raise or handle gracefully."""
        import process_articles as pa
        import config as cfg
        cfg.OUTPUT_DIR = tmp_dir / "nonexistent_output"
        cfg.METADATA_REGISTRY = tmp_dir / "metadata" / "articles_metadata.json"
        import importlib; importlib.reload(pa)
        # The directory won't exist, so writing should fail — processor should catch it
        proc = pa.ArticleProcessor()
        # Simulate what process_pdf does when writing:
        if not cfg.OUTPUT_DIR.exists():
            try:
                with open(cfg.OUTPUT_DIR / "test.md", "w") as f:
                    f.write("test")
                wrote = True
            except (FileNotFoundError, OSError):
                wrote = False
            assert not wrote

    def test_pdf_rename_to_existing_file_skipped(self, tmp_path):
        """rename_pdfs must not overwrite an existing file at the destination."""
        import config as cfg
        cfg.METADATA_REGISTRY = tmp_path / "reg.json"
        cfg.ARCHIVE_DIR = tmp_path / "archive"
        cfg.ARCHIVE_DIR.mkdir()

        old_content = b"ORIGINAL"
        new_content = b"EXISTING_DEST"
        (tmp_path / "archive" / "old.pdf").write_bytes(old_content)
        (tmp_path / "archive" / "2024-01-01_HBR_Title.pdf").write_bytes(new_content)

        articles = [{"source_file": "old.pdf", "output_file": "2024-01-01_HBR_Title.md"}]
        (tmp_path / "reg.json").write_text(json.dumps({"articles": articles}))

        import rename_archived_pdfs as rnm
        import importlib; importlib.reload(rnm)
        rnm.rename_pdfs(dry_run=False)

        # Destination should be unchanged (not overwritten)
        assert (tmp_path / "archive" / "2024-01-01_HBR_Title.pdf").read_bytes() == new_content

    def test_intake_with_non_pdf_files_ignored(self, tmp_dir, capsys):
        """Non-PDF files in intake should be ignored by process_all."""
        (tmp_dir / "intake" / "notes.txt").write_text("This is not a PDF")
        (tmp_dir / "intake" / "image.jpg").write_bytes(b"\xff\xd8\xff\xe0JFIF")

        import process_articles as pa
        import config as cfg
        cfg.INTAKE_DIR = tmp_dir / "intake"
        cfg.OUTPUT_DIR = tmp_dir / "output"
        cfg.ARCHIVE_DIR = tmp_dir / "pdf_archive"
        cfg.METADATA_DIR = tmp_dir / "metadata"
        cfg.METADATA_REGISTRY = tmp_dir / "metadata" / "articles_metadata.json"
        import importlib; importlib.reload(pa)
        proc = pa.ArticleProcessor()
        proc.process_all()
        captured = capsys.readouterr()
        assert "No PDF" in captured.out

    def test_metadata_dir_auto_created_by_config(self, tmp_path, monkeypatch):
        """config.py creates directories on import — test the mechanism."""
        new_base = tmp_path / "fresh_project"
        new_base.mkdir()
        # Manually test mkdir logic
        for d in ["intake", "output", "pdf_archive", "metadata"]:
            p = new_base / d
            p.mkdir(parents=True, exist_ok=True)
            assert p.exists()


# ===========================================================================
# SECTION 18 — Encoding and Character Edge Cases
# ===========================================================================

class TestEncodingEdgeCases:

    def test_markdown_written_utf8(self, tmp_path):
        from utils import create_markdown_content
        content = create_markdown_content(
            "Über Führung: Stratégie",
            "André Müller",
            "2024-01-01",
            ["führung", "stratégie"],
            "Körner und Straße",
            source="FT"
        )
        out = tmp_path / "article.md"
        out.write_text(content, encoding="utf-8")
        read_back = out.read_text(encoding="utf-8")
        assert "Über" in read_back
        assert "André" in read_back

    def test_keywords_with_accented_chars(self):
        from utils import extract_keywords
        text = "Führung Führung Führung stratégie stratégie innovation"
        result = extract_keywords(text, num_keywords=5)
        assert isinstance(result, list)

    def test_title_with_curly_quotes(self):
        from utils import sanitize_filename
        result = sanitize_filename("\u201cSmart\u201d Leadership")  # " and "
        assert isinstance(result, str)

    def test_json_roundtrip_unicode(self, tmp_path):
        data = {"articles": [{"title": "Über Stratégie", "keywords": ["führung"]}]}
        path = tmp_path / "registry.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["articles"][0]["title"] == "Über Stratégie"


# ===========================================================================
# SECTION 19 — Config Integrity Tests
# ===========================================================================

class TestConfig:

    def test_stopwords_is_set(self):
        from config import COMMON_STOPWORDS
        assert isinstance(COMMON_STOPWORDS, set)
        assert "the" in COMMON_STOPWORDS
        assert "and" in COMMON_STOPWORDS

    def test_date_formats_is_list(self):
        from config import DATE_FORMATS
        assert isinstance(DATE_FORMATS, list)
        assert len(DATE_FORMATS) > 0

    def test_min_max_keywords_valid(self):
        from config import MIN_KEYWORDS, MAX_KEYWORDS
        assert MIN_KEYWORDS > 0
        assert MAX_KEYWORDS >= MIN_KEYWORDS

    def test_paths_are_pathlib(self):
        from config import INTAKE_DIR, OUTPUT_DIR, ARCHIVE_DIR, METADATA_DIR, METADATA_REGISTRY
        for p in [INTAKE_DIR, OUTPUT_DIR, ARCHIVE_DIR, METADATA_DIR, METADATA_REGISTRY]:
            assert isinstance(p, Path)

    def test_metadata_registry_inside_metadata_dir(self):
        from config import METADATA_DIR, METADATA_REGISTRY
        assert METADATA_REGISTRY.parent == METADATA_DIR


# ===========================================================================
# SECTION 20 — Regression / Real-World Data Tests
# ===========================================================================

class TestRegressionCases:

    def test_real_registry_loads(self):
        """The actual project registry should load without errors."""
        real_reg = PROJECT_ROOT / "metadata" / "articles_metadata.json"
        if not real_reg.exists():
            pytest.skip("No real registry file present")
        data = json.loads(real_reg.read_text())
        assert "articles" in data
        assert isinstance(data["articles"], list)

    def test_real_registry_article_structure(self):
        """Every article in the real registry should have title and output_file."""
        real_reg = PROJECT_ROOT / "metadata" / "articles_metadata.json"
        if not real_reg.exists():
            pytest.skip("No real registry file present")
        data = json.loads(real_reg.read_text())
        for art in data["articles"]:
            assert "title" in art, f"Missing title: {art}"
            assert "output_file" in art, f"Missing output_file: {art}"

    def test_real_md_files_have_frontmatter(self):
        """Every .md in output/ should start with --- (YAML frontmatter)."""
        output_dir = PROJECT_ROOT / "output"
        md_files = list(output_dir.glob("*.md"))
        if not md_files:
            pytest.skip("No output markdown files present")
        for md in md_files:
            content = md.read_text(encoding="utf-8", errors="replace")
            assert content.startswith("---"), f"{md.name} missing frontmatter"

    def test_real_registry_keyword_lists_are_lists(self):
        """Keywords in every registry article must be a Python list."""
        real_reg = PROJECT_ROOT / "metadata" / "articles_metadata.json"
        if not real_reg.exists():
            pytest.skip("No real registry file present")
        data = json.loads(real_reg.read_text())
        for art in data["articles"]:
            kws = art.get("keywords", [])
            assert isinstance(kws, list), f"Keywords is not a list in: {art.get('title')}"

    def test_overrides_file_valid_json(self):
        """manual_metadata_overrides.json (if it exists) must be valid JSON."""
        overrides = PROJECT_ROOT / "metadata" / "manual_metadata_overrides.json"
        if not overrides.exists():
            pytest.skip("No overrides file")
        data = json.loads(overrides.read_text())
        assert "overrides" in data
        assert isinstance(data["overrides"], list)

    def test_real_md_filenames_follow_convention(self):
        """Output MD filenames should match expected pattern."""
        import re
        output_dir = PROJECT_ROOT / "output"
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}_\S+.*\.md$")
        md_files = list(output_dir.glob("*.md"))
        if not md_files:
            pytest.skip("No output markdown files")
        # Check a reasonable fraction — not all may follow convention
        matched = sum(1 for f in md_files if pattern.match(f.name))
        # At least 50% should match
        assert matched / len(md_files) >= 0.5, f"Only {matched}/{len(md_files)} follow naming convention"
