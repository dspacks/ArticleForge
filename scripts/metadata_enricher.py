#!/usr/bin/env python3
"""
Metadata Enricher

Takes a partially-populated article record (already extracted by utils.py)
and fills in missing fields using:
  1. CrossRef DOI lookup (if DOI is present)
  2. CrossRef title search (if title + author available, no DOI)

Tracks extraction_sources and extraction_confidence per field.
Never overwrites a high-confidence value (confidence > 0.5).

Usage:
    from metadata_enricher import enrich
    record = enrich(record, text)
"""

from typing import Dict, List, Optional

from crossref_client import CrossRefClient

# ---------------------------------------------------------------------------
# Confidence thresholds
# ---------------------------------------------------------------------------

CONFIDENCE_HIGH = 0.9       # PDF metadata, validated DOI lookup
CONFIDENCE_MEDIUM = 0.6     # Text extraction, CrossRef title search hit
CONFIDENCE_LOW = 0.3        # Heuristic / fallback
OVERWRITE_THRESHOLD = 0.5   # Don't overwrite values above this confidence

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_client: Optional[CrossRefClient] = None


def _get_client() -> CrossRefClient:
    """Lazy-init CrossRef client (singleton per session)."""
    global _client
    if _client is None:
        _client = CrossRefClient()
    return _client


def _set_field(record: Dict, field: str, value, source: str, confidence: float) -> bool:
    """
    Set a field in the record only if:
      - The field is missing/None, OR
      - The existing field's confidence is below OVERWRITE_THRESHOLD

    Also updates extraction_sources and extraction_confidence dicts.

    Returns True if the field was updated.
    """
    if value is None:
        return False

    existing_confidence = record.get('extraction_confidence', {}).get(field, 0.0)
    if existing_confidence > OVERWRITE_THRESHOLD:
        return False  # Don't overwrite confident value

    record[field] = value
    record.setdefault('extraction_sources', {})[field] = source
    record.setdefault('extraction_confidence', {})[field] = confidence
    return True


def _apply_crossref(record: Dict, crossref_data: Dict, source_label: str) -> None:
    """Apply fields from a CrossRef record to the article record."""
    confidence = CONFIDENCE_HIGH if source_label == 'crossref_doi' else CONFIDENCE_MEDIUM

    # DOI
    if crossref_data.get('doi'):
        _set_field(record, 'doi', crossref_data['doi'], source_label, confidence)

    # Authors (structured list)
    if crossref_data.get('authors'):
        _set_field(record, 'authors', crossref_data['authors'], source_label, confidence)
        # Keep legacy 'author' string in sync
        full_names = [a.get('full', '') for a in crossref_data['authors'] if a.get('full')]
        if full_names:
            _set_field(record, 'author', '; '.join(full_names), source_label, confidence)

    # Publication details
    pub = record.setdefault('publication', {})
    if crossref_data.get('journal') and not pub.get('journal'):
        pub['journal'] = crossref_data['journal']
        record.setdefault('extraction_sources', {})['publication.journal'] = source_label
        record.setdefault('extraction_confidence', {})['publication.journal'] = confidence

    if crossref_data.get('volume') and not pub.get('volume'):
        pub['volume'] = crossref_data['volume']
    if crossref_data.get('issue') and not pub.get('issue'):
        pub['issue'] = crossref_data['issue']
    if crossref_data.get('pages') and not pub.get('pages'):
        pub['pages'] = crossref_data['pages']

    # URL
    if crossref_data.get('url'):
        _set_field(record, 'url', crossref_data['url'], source_label, confidence)

    # Abstract
    if crossref_data.get('abstract'):
        _set_field(record, 'abstract', crossref_data['abstract'], source_label, confidence)

    # Date / year
    if crossref_data.get('year') and not record.get('date'):
        _set_field(record, 'date', crossref_data['year'], source_label, CONFIDENCE_LOW)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def enrich(record: Dict, text: str) -> Dict:
    """
    Enrich an article record with data from CrossRef and local extractors.

    Strategy:
      1. If DOI present → CrossRef DOI lookup → fill missing fields
      2. Else if title + (author or keywords) → CrossRef title search
      3. Mark schema_version = 2

    Args:
        record: Article metadata dict (will be modified in place)
        text: Full extracted article text (used for local extractors)

    Returns:
        Enriched record (same object, modified in place)
    """
    # Always mark schema version
    record['schema_version'] = 2

    # Ensure v2 containers exist
    record.setdefault('authors', [])
    record.setdefault('publication', {})
    record.setdefault('extraction_confidence', {})
    record.setdefault('extraction_sources', {})

    doi = record.get('doi')
    title = record.get('title', '')
    author = record.get('author', '')

    try:
        client = _get_client()

        if doi:
            crossref_data = client.lookup_doi(doi)
            if crossref_data:
                _apply_crossref(record, crossref_data, 'crossref_doi')
        elif title:
            # Extract last name of first author for better search precision
            author_last = None
            if author:
                # Take last word of first author segment
                first_author_segment = author.split(';')[0].strip()
                author_last = first_author_segment.split()[-1] if first_author_segment else None

            crossref_data = client.search_by_title(title, author_last=author_last)
            if crossref_data:
                _apply_crossref(record, crossref_data, 'crossref_title_search')

    except Exception as e:
        print(f"  Warning: CrossRef enrichment failed: {e}")

    return record
