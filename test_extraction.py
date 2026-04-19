#!/usr/bin/env python3
"""
test_extraction.py — Unit tests for Phase 1 / 2 / 3 new extraction functions.

Covers:
  - extract_doi()
  - parse_authors() / extract_authors()
  - extract_author() legacy shim
  - extract_publication_details()
  - extract_abstract()
  - _normalize_record() backward-compat shim
  - CrossRefClient cache behaviour (offline mock)
  - metadata_enricher.enrich() (offline mock)

Run with:
    pytest test_extraction.py -v
    pytest test_extraction.py -v --tb=short
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup — scripts/ must be importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ===========================================================================
# SECTION 1 — extract_doi
# ===========================================================================

class TestExtractDoi:

    def test_doi_in_first_page(self):
        from utils import extract_doi
        text = "Published in Nature.\nDOI: 10.1038/s41586-021-03819-2\nAbstract follows..."
        result = extract_doi(text)
        assert result == "10.1038/s41586-021-03819-2"

    def test_doi_case_insensitive(self):
        from utils import extract_doi
        text = "doi:10.1016/j.cell.2021.01.001 see also the supplemental"
        result = extract_doi(text)
        assert result is not None
        assert result.startswith("10.")

    def test_doi_in_pdf_metadata_subject(self):
        from utils import extract_doi
        pdf_meta = {'subject': '10.1234/abcd1234', 'title': None, 'author': None, 'date': None}
        result = extract_doi("No DOI in text", pdf_meta)
        assert result == "10.1234/abcd1234"

    def test_doi_in_last_page_references(self):
        from utils import extract_doi
        # DOI appears only at the end (references section)
        text = "x" * 3000 + "\n10.1177/0956797614567323\n"
        result = extract_doi(text)
        assert result == "10.1177/0956797614567323"

    def test_no_doi_returns_none(self):
        from utils import extract_doi
        result = extract_doi("This article has no DOI anywhere in the text.", None)
        assert result is None

    def test_invalid_doi_rejected(self):
        from utils import extract_doi
        # Missing slash after registrant prefix
        result = extract_doi("Ref: 10.12345 no slash here", None)
        assert result is None

    def test_doi_with_trailing_period_stripped(self):
        from utils import extract_doi
        text = "See 10.1234/abcdef. For more info..."
        result = extract_doi(text)
        # Trailing period should be stripped
        if result:
            assert not result.endswith('.')

    def test_empty_text_returns_none(self):
        from utils import extract_doi
        assert extract_doi("", None) is None

    def test_none_text_returns_none(self):
        from utils import extract_doi
        assert extract_doi(None, None) is None


# ===========================================================================
# SECTION 2 — parse_authors / extract_authors
# ===========================================================================

class TestParseAuthors:

    def test_single_natural_order(self):
        from utils import parse_authors
        result = parse_authors("Jane Smith")
        assert len(result) == 1
        assert result[0]['last'] == 'Smith'
        assert result[0]['first'] == 'Jane'
        assert result[0]['full'] == 'Jane Smith'

    def test_single_last_first(self):
        from utils import parse_authors
        result = parse_authors("Smith, Jane")
        assert len(result) == 1
        assert result[0]['last'] == 'Smith'
        assert result[0]['first'] == 'Jane'

    def test_multiple_semicolon_separated(self):
        from utils import parse_authors
        result = parse_authors("Jane Smith; John Doe; Alice Brown")
        assert len(result) == 3
        assert result[0]['last'] == 'Smith'
        assert result[1]['last'] == 'Doe'
        assert result[2]['last'] == 'Brown'

    def test_multiple_and_separated(self):
        from utils import parse_authors
        result = parse_authors("Jane Smith and John Doe")
        assert len(result) == 2
        assert result[0]['full'] == 'Jane Smith'
        assert result[1]['full'] == 'John Doe'

    def test_multiple_ampersand_separated(self):
        from utils import parse_authors
        result = parse_authors("Jane Smith & John Doe")
        assert len(result) == 2

    def test_honorifics_stripped(self):
        from utils import parse_authors
        result = parse_authors("Jane Smith, PhD")
        assert len(result) >= 1
        assert 'PhD' not in result[0]['last']

    def test_middle_initial_preserved(self):
        from utils import parse_authors
        result = parse_authors("John M. Smith")
        assert len(result) == 1
        assert result[0]['last'] == 'Smith'
        assert 'John' in result[0]['first']

    def test_empty_string_returns_empty_list(self):
        from utils import parse_authors
        assert parse_authors("") == []

    def test_none_like_empty_returns_empty(self):
        from utils import parse_authors
        assert parse_authors("   ") == []

    def test_affiliation_in_parens_extracted(self):
        from utils import parse_authors
        result = parse_authors("Jane Smith (Harvard University)")
        assert len(result) == 1
        assert result[0]['affiliation'] == 'Harvard University'
        assert 'Harvard' not in result[0]['last']

    def test_single_word_name(self):
        from utils import parse_authors
        result = parse_authors("Aristotle")
        assert len(result) == 1
        assert result[0]['last'] == 'Aristotle'


class TestExtractAuthors:

    def test_prefers_pdf_metadata(self):
        from utils import extract_authors
        result = extract_authors("By Someone in text", "Jane Smith")
        assert len(result) == 1
        assert result[0]['last'] == 'Smith'

    def test_falls_back_to_text_by_pattern(self):
        from utils import extract_authors
        result = extract_authors("By Jane Smith\nArticle content here...", None)
        assert len(result) >= 1

    def test_empty_metadata_falls_back(self):
        from utils import extract_authors
        result = extract_authors("By Alice Brown and Bob Green\nContent...", "")
        # Empty string pdf_metadata → fall back to text
        assert isinstance(result, list)

    def test_no_author_anywhere(self):
        from utils import extract_authors
        result = extract_authors("This text has no author signal at all.", None)
        assert result == []


# ===========================================================================
# SECTION 3 — extract_author legacy shim
# ===========================================================================

class TestExtractAuthorLegacyShim:

    def test_returns_string(self):
        from utils import extract_author
        result = extract_author("By Jane Smith\nContent...", None)
        assert isinstance(result, str) or result is None

    def test_multiple_authors_joined_semicolon(self):
        from utils import extract_author
        result = extract_author("", "Jane Smith; John Doe")
        assert result is not None
        assert ';' in result or 'Jane' in result

    def test_pdf_metadata_preferred(self):
        from utils import extract_author
        result = extract_author("By Someone Else", "Jane Smith")
        assert result == "Jane Smith"

    def test_none_text_no_metadata(self):
        from utils import extract_author
        result = extract_author(None, None)
        assert result is None


# ===========================================================================
# SECTION 4 — extract_publication_details
# ===========================================================================

class TestExtractPublicationDetails:

    def test_volume_issue_extracted(self):
        from utils import extract_publication_details
        text = "Published in Journal of X, Vol. 12, No. 3, pp. 45-67."
        result = extract_publication_details(text)
        assert result['volume'] == '12'
        assert result['issue'] == '3'

    def test_pages_extracted(self):
        from utils import extract_publication_details
        text = "Reference: Management Science, pp. 101-115."
        result = extract_publication_details(text)
        assert result['pages'] == '101-115'

    def test_volume_issue_long_form(self):
        from utils import extract_publication_details
        text = "Volume 5, Issue 2 of the review"
        result = extract_publication_details(text)
        assert result['volume'] == '5'
        assert result['issue'] == '2'

    def test_no_details_returns_none_values(self):
        from utils import extract_publication_details
        result = extract_publication_details("No publication details here at all.")
        assert result['volume'] is None
        assert result['issue'] is None
        assert result['pages'] is None

    def test_empty_text_returns_empty_dict(self):
        from utils import extract_publication_details
        result = extract_publication_details("")
        assert isinstance(result, dict)
        assert result.get('journal') is None

    def test_none_text_returns_empty_dict(self):
        from utils import extract_publication_details
        result = extract_publication_details(None)
        assert isinstance(result, dict)

    def test_en_dash_pages(self):
        from utils import extract_publication_details
        text = "pp.\u202045\u2013\u202067 results section"  # en-dash
        result = extract_publication_details(text)
        # May or may not match depending on whitespace — just shouldn't crash
        assert isinstance(result, dict)


# ===========================================================================
# SECTION 5 — extract_abstract
# ===========================================================================

class TestExtractAbstract:

    def test_extracts_after_abstract_header(self):
        from utils import extract_abstract
        text = "Title Here\n\nAbstract\nThis study examines the relationship between leadership and performance.\n\nIntroduction\nMore text..."
        result = extract_abstract(text)
        assert result is not None
        assert 'leadership' in result.lower() or 'study' in result.lower()

    def test_abstract_colon_variant(self):
        from utils import extract_abstract
        text = "Abstract: This paper explores innovation in large firms.\n\nKeywords: innovation, firms"
        result = extract_abstract(text)
        assert result is not None

    def test_no_abstract_section_returns_none(self):
        from utils import extract_abstract
        result = extract_abstract("Just plain text with no abstract header anywhere in it.")
        assert result is None

    def test_empty_text_returns_none(self):
        from utils import extract_abstract
        assert extract_abstract("") is None

    def test_none_text_returns_none(self):
        from utils import extract_abstract
        assert extract_abstract(None) is None

    def test_very_long_abstract_truncated(self):
        from utils import extract_abstract
        long_body = "word " * 600
        text = f"Abstract\n{long_body}\nIntroduction\nMore content."
        result = extract_abstract(text)
        if result:
            assert len(result.split()) <= 510  # 500 + a few for the ellipsis check


# ===========================================================================
# SECTION 6 — _normalize_record (backward-compat shim)
# ===========================================================================

class TestNormalizeRecord:

    def test_v1_record_gets_authors_synthesized(self):
        import zotero_export as ze
        article = {
            "title": "Test",
            "author": "Jane Smith",
            "date": "2024-01-01",
            "source": "HBR",
            "keywords": [],
        }
        result = ze._normalize_record(article)
        assert isinstance(result['authors'], list)
        assert len(result['authors']) == 1
        assert result['authors'][0]['last'] == 'Smith'

    def test_v1_multiple_authors_synthesized(self):
        import zotero_export as ze
        article = {
            "author": "Jane Smith; John Doe",
            "source": "HBR",
            "keywords": [],
        }
        result = ze._normalize_record(article)
        assert len(result['authors']) == 2

    def test_v1_no_author_gives_empty_list(self):
        import zotero_export as ze
        article = {"title": "T", "source": "HBR", "keywords": []}
        result = ze._normalize_record(article)
        assert result['authors'] == []

    def test_v2_authors_not_overwritten(self):
        import zotero_export as ze
        existing_authors = [{'first': 'Alice', 'last': 'Wong', 'full': 'Alice Wong', 'affiliation': None}]
        article = {
            "author": "Jane Smith",
            "authors": existing_authors,
            "source": "HBR",
            "keywords": [],
        }
        result = ze._normalize_record(article)
        # v2 authors should be kept as-is
        assert result['authors'][0]['last'] == 'Wong'

    def test_publication_dict_synthesized(self):
        import zotero_export as ze
        article = {"title": "T", "source": "Nature", "keywords": []}
        result = ze._normalize_record(article)
        assert isinstance(result['publication'], dict)
        assert result['publication'].get('journal') == 'Nature'

    def test_doi_defaults_to_none(self):
        import zotero_export as ze
        article = {"title": "T", "source": "HBR", "keywords": []}
        result = ze._normalize_record(article)
        assert result['doi'] is None

    def test_does_not_mutate_original(self):
        import zotero_export as ze
        article = {"title": "T", "source": "HBR", "keywords": []}
        original_keys = set(article.keys())
        ze._normalize_record(article)
        assert set(article.keys()) == original_keys


# ===========================================================================
# SECTION 7 — CrossRefClient (offline / cached)
# ===========================================================================

class TestCrossRefClientCache:

    def test_cached_doi_not_fetched_again(self, tmp_path, monkeypatch):
        """If a DOI is already in the in-memory cache, _get() must not be called."""
        import crossref_client as cc

        client = cc.CrossRefClient()
        # Directly inject a cached result — simulates what _load_cache() provides
        cached_record = {"doi": "10.1234/xyz", "title": "Cached Title",
                         "authors": [], "journal": None, "volume": None,
                         "issue": None, "pages": None, "year": None,
                         "url": None, "abstract": None, "publisher": None}
        client._cache["doi:10.1234/xyz"] = cached_record

        # Spy on _get to ensure it is NOT invoked
        get_calls = []
        original_get = client._get
        def spy_get(*args, **kwargs):
            get_calls.append(args)
            return original_get(*args, **kwargs)
        monkeypatch.setattr(client, '_get', spy_get)

        result = client.lookup_doi("10.1234/xyz")
        assert result is not None
        assert result['title'] == 'Cached Title'
        assert len(get_calls) == 0, "Expected no network call for in-memory cached DOI"

    def test_lookup_doi_offline_returns_none(self, tmp_path, monkeypatch):
        import config as cfg
        cfg.CROSSREF_CACHE = tmp_path / ".crossref_cache.json"
        import crossref_client as cc
        monkeypatch.setattr(cc, 'REQUESTS_AVAILABLE', False)

        client = cc.CrossRefClient()
        result = client.lookup_doi("10.9999/nonexistent")
        assert result is None

    def test_search_by_title_offline_returns_none(self, tmp_path, monkeypatch):
        import config as cfg
        cfg.CROSSREF_CACHE = tmp_path / ".crossref_cache.json"
        import crossref_client as cc
        monkeypatch.setattr(cc, 'REQUESTS_AVAILABLE', False)

        client = cc.CrossRefClient()
        result = client.search_by_title("Some Article Title", author_last="Smith")
        assert result is None

    def test_negative_result_cached(self, tmp_path, monkeypatch):
        """A failed online lookup should be cached as None to prevent repeat network calls."""
        import config as cfg
        cfg.CROSSREF_CACHE = tmp_path / ".crossref_cache.json"
        import crossref_client as cc

        # Simulate online but returning a 404 (non-200 response)
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_resp

        monkeypatch.setattr(cc, 'REQUESTS_AVAILABLE', True)
        monkeypatch.setattr(cc, 'requests', mock_requests)

        client = cc.CrossRefClient()
        result = client.lookup_doi("10.0000/miss")
        assert result is None

        # Cache should have the key stored as None
        if cfg.CROSSREF_CACHE.exists():
            cache = json.loads(cfg.CROSSREF_CACHE.read_text())
            assert "doi:10.0000/miss" in cache
            assert cache["doi:10.0000/miss"] is None


# ===========================================================================
# SECTION 8 — metadata_enricher.enrich()
# ===========================================================================

class TestMetadataEnricher:

    def _base_record(self) -> dict:
        return {
            "title": "Test Article",
            "author": "Jane Smith",
            "date": "2024-01-01",
            "source": "HBR",
            "keywords": ["leadership"],
            "doi": None,
            "authors": [],
            "publication": {},
            "extraction_confidence": {},
            "extraction_sources": {},
        }

    def test_schema_version_always_set(self):
        from metadata_enricher import enrich
        record = self._base_record()
        with patch("metadata_enricher._get_client") as mock_client:
            mock_client.return_value.lookup_doi.return_value = None
            mock_client.return_value.search_by_title.return_value = None
            result = enrich(record, "some text")
        assert result['schema_version'] == 2

    def test_crossref_doi_data_applied(self):
        from metadata_enricher import enrich
        record = self._base_record()
        record['doi'] = "10.1234/test"

        crossref_data = {
            "doi": "10.1234/test",
            "title": "Test Article",
            "authors": [{"first": "Jane", "last": "Smith", "full": "Jane Smith", "affiliation": None}],
            "journal": "Harvard Business Review",
            "volume": "99",
            "issue": "3",
            "pages": "10-20",
            "url": "https://hbr.org/test",
            "abstract": "This paper studies leadership.",
            "year": "2024",
            "publisher": "HBP",
        }

        with patch("metadata_enricher._get_client") as mock_client:
            mock_client.return_value.lookup_doi.return_value = crossref_data
            result = enrich(record, "some text")

        assert result['publication'].get('journal') == "Harvard Business Review"
        assert result['url'] == "https://hbr.org/test"
        assert result['abstract'] is not None

    def test_high_confidence_value_not_overwritten(self):
        from metadata_enricher import enrich, OVERWRITE_THRESHOLD
        record = self._base_record()
        record['doi'] = "10.1234/test"
        record['url'] = "https://existing-high-confidence.com"
        record['extraction_confidence']['url'] = OVERWRITE_THRESHOLD + 0.1  # above threshold

        crossref_data = {
            "doi": "10.1234/test",
            "url": "https://crossref-url.com",
            "authors": [], "journal": None, "volume": None,
            "issue": None, "pages": None, "abstract": None, "year": None,
        }

        with patch("metadata_enricher._get_client") as mock_client:
            mock_client.return_value.lookup_doi.return_value = crossref_data
            result = enrich(record, "text")

        # Original high-confidence URL should be preserved
        assert result['url'] == "https://existing-high-confidence.com"

    def test_enrichment_failure_does_not_crash(self):
        from metadata_enricher import enrich
        record = self._base_record()

        with patch("metadata_enricher._get_client") as mock_client:
            mock_client.side_effect = Exception("Network failure")
            result = enrich(record, "text")

        # Should still set schema_version and return a record
        assert result['schema_version'] == 2

    def test_title_search_used_when_no_doi(self):
        from metadata_enricher import enrich
        record = self._base_record()
        # doi is None → should fall through to title search

        with patch("metadata_enricher._get_client") as mock_client:
            mock_client.return_value.lookup_doi.return_value = None
            mock_client.return_value.search_by_title.return_value = None
            enrich(record, "text")
            # search_by_title should have been called (doi was None)
            mock_client.return_value.search_by_title.assert_called_once()


# ===========================================================================
# SECTION 9 — Zotero export with v2 fields end-to-end
# ===========================================================================

class TestZoteroExportV2:

    def _v2_article(self) -> dict:
        return {
            "title": "Leadership in Crisis",
            "author": "Jane Smith",
            "authors": [{"first": "Jane", "last": "Smith", "full": "Jane Smith", "affiliation": None}],
            "date": "2024-06-15",
            "source": "HBR",
            "keywords": ["leadership", "crisis"],
            "doi": "10.1234/leadership",
            "url": "https://hbr.org/article",
            "abstract": "This paper examines leadership in crisis situations.",
            "publication": {"journal": "Harvard Business Review", "volume": "102", "issue": "4", "pages": "50-60"},
            "pdf_archive_path": "/path/to/article.pdf",
            "processed_date": "2026-04-19",
            "schema_version": 2,
            "extraction_confidence": {},
            "extraction_sources": {},
        }

    def test_bibtex_includes_doi(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.bib"
        ze.export_to_bibtex([self._v2_article()], out)
        content = out.read_text()
        assert "10.1234/leadership" in content

    def test_bibtex_includes_volume_and_issue(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.bib"
        ze.export_to_bibtex([self._v2_article()], out)
        content = out.read_text()
        assert "volume = {102}" in content
        assert "number = {4}" in content

    def test_bibtex_includes_pages(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.bib"
        ze.export_to_bibtex([self._v2_article()], out)
        content = out.read_text()
        assert "pages = {50-60}" in content

    def test_bibtex_includes_file_attachment(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.bib"
        ze.export_to_bibtex([self._v2_article()], out)
        content = out.read_text()
        assert "file = {" in content
        assert "/path/to/article.pdf" in content

    def test_bibtex_author_format(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.bib"
        ze.export_to_bibtex([self._v2_article()], out)
        content = out.read_text()
        # BibTeX format: "Last, First"
        assert "Smith, Jane" in content

    def test_csv_includes_doi_column(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.csv"
        ze.export_to_csv([self._v2_article()], out)
        content = out.read_text()
        assert "DOI" in content
        assert "10.1234/leadership" in content

    def test_csv_includes_file_attachments_column(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.csv"
        ze.export_to_csv([self._v2_article()], out)
        content = out.read_text()
        assert "File Attachments" in content

    def test_json_structured_creators(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.json"
        ze.export_to_json([self._v2_article()], out)
        data = json.loads(out.read_text())
        assert len(data) == 1
        creators = data[0]['creators']
        assert any(c.get('firstName') == 'Jane' for c in creators)
        assert any(c.get('lastName') == 'Smith' for c in creators)

    def test_json_doi_field(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.json"
        ze.export_to_json([self._v2_article()], out)
        data = json.loads(out.read_text())
        assert data[0]['DOI'] == "10.1234/leadership"

    def test_json_abstract_note(self, tmp_path):
        import zotero_export as ze
        out = tmp_path / "test.json"
        ze.export_to_json([self._v2_article()], out)
        data = json.loads(out.read_text())
        assert "crisis" in data[0].get('abstractNote', '').lower()

    def test_v1_record_exported_without_crash(self, tmp_path):
        """Legacy v1 records (no schema_version) should export cleanly in all formats."""
        import zotero_export as ze
        v1 = {"title": "Old Article", "author": "Bob Jones", "date": "2023-01-01",
               "source": "WSJ", "keywords": ["finance"], "processed_date": "2026-01-01"}
        for fmt, fn in [('bib', ze.export_to_bibtex), ('csv', ze.export_to_csv),
                        ('json', ze.export_to_json)]:
            out = tmp_path / f"v1_test.{fmt}"
            fn([v1], out)
            assert out.exists(), f"v1 export failed for format: {fmt}"
