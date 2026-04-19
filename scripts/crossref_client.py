#!/usr/bin/env python3
"""
CrossRef API Client

Provides DOI lookup and title-based search against the CrossRef REST API.
Results are cached to metadata/.crossref_cache.json to minimize network calls.
Falls back gracefully when offline or when the API returns no useful result.

Usage (direct):
    from crossref_client import CrossRefClient
    client = CrossRefClient()
    record = client.lookup_doi("10.1234/example")
    record = client.search_by_title("My Article Title", author_last="Smith")
"""

import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: 'requests' not installed. CrossRef lookups will be skipped.")

from config import CROSSREF_CACHE

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CROSSREF_WORKS_URL = "https://api.crossref.org/works/{doi}"
CROSSREF_SEARCH_URL = "https://api.crossref.org/works"
POLITE_EMAIL = "spacks@gmail.com"        # Identifies us to CrossRef for polite pool
REQUEST_TIMEOUT = 10                      # seconds
FUZZY_MATCH_THRESHOLD = 0.80             # SequenceMatcher ratio for title match


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load_cache() -> Dict:
    """Load CrossRef cache from disk, or return empty dict."""
    if CROSSREF_CACHE.exists():
        try:
            return json.loads(CROSSREF_CACHE.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_cache(cache: Dict) -> None:
    """Persist CrossRef cache to disk."""
    try:
        CROSSREF_CACHE.write_text(
            json.dumps(cache, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
    except IOError as e:
        print(f"  Warning: Could not save CrossRef cache: {e}")


# ---------------------------------------------------------------------------
# Response normalization
# ---------------------------------------------------------------------------

def _normalize_message(message: Dict) -> Dict:
    """
    Normalize a CrossRef 'message' dict into a flat record used by the enricher.

    Returns dict with keys (all Optional):
        doi, title, authors, journal, volume, issue, pages,
        year, url, abstract, publisher
    """
    record: Dict = {}

    # DOI
    record['doi'] = message.get('DOI')

    # Title (CrossRef returns a list)
    titles = message.get('title', [])
    record['title'] = titles[0] if titles else None

    # Authors
    authors: List[Dict] = []
    for contrib in message.get('author', []):
        entry = {
            'first': contrib.get('given', ''),
            'last': contrib.get('family', ''),
            'full': f"{contrib.get('given', '')} {contrib.get('family', '')}".strip(),
            'affiliation': None,
        }
        affs = contrib.get('affiliation', [])
        if affs and isinstance(affs, list) and affs[0].get('name'):
            entry['affiliation'] = affs[0]['name']
        authors.append(entry)
    record['authors'] = authors

    # Journal
    container = message.get('container-title', [])
    record['journal'] = container[0] if container else None

    # Volume / Issue / Pages
    record['volume'] = message.get('volume')
    record['issue'] = message.get('issue')
    record['pages'] = message.get('page')

    # Publication year
    issued = message.get('issued', {})
    date_parts = issued.get('date-parts', [[]])
    if date_parts and date_parts[0]:
        record['year'] = str(date_parts[0][0])
    else:
        record['year'] = None

    # URL
    record['url'] = message.get('URL') or message.get('resource', {}).get('primary', {}).get('URL')

    # Abstract (CrossRef sometimes provides it; strip JATS XML tags)
    abstract_raw = message.get('abstract', '')
    if abstract_raw:
        abstract_clean = re.sub(r'<[^>]+>', ' ', abstract_raw).strip()
        abstract_clean = re.sub(r'\s+', ' ', abstract_clean)
        record['abstract'] = abstract_clean if len(abstract_clean) > 20 else None
    else:
        record['abstract'] = None

    record['publisher'] = message.get('publisher')

    return record


# ---------------------------------------------------------------------------
# Main client class
# ---------------------------------------------------------------------------

class CrossRefClient:
    """
    Thin wrapper around the CrossRef REST API with local disk cache.

    All network failures are caught; methods return None on failure.
    """

    def __init__(self):
        self._cache: Dict = _load_cache()

    def _get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Perform a GET request against CrossRef. Returns parsed JSON or None.
        """
        if not REQUESTS_AVAILABLE:
            return None
        headers = {'User-Agent': f'ArticleForge/1.0 (mailto:{POLITE_EMAIL})'}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            print(f"  Warning: CrossRef request failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup_doi(self, doi: str) -> Optional[Dict]:
        """
        Look up a DOI via CrossRef and return a normalized metadata dict.

        Result is cached by DOI key.

        Args:
            doi: DOI string e.g. "10.1234/abcd"

        Returns:
            Normalized metadata dict or None
        """
        cache_key = f"doi:{doi}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = CROSSREF_WORKS_URL.format(doi=doi)
        data = self._get(url)
        if data and data.get('status') == 'ok':
            normalized = _normalize_message(data['message'])
            self._cache[cache_key] = normalized
            _save_cache(self._cache)
            return normalized

        # Cache negative result to avoid repeat lookups
        self._cache[cache_key] = None
        _save_cache(self._cache)
        return None

    def search_by_title(self, title: str, author_last: Optional[str] = None) -> Optional[Dict]:
        """
        Search CrossRef by title (and optionally author last name).

        Uses fuzzy matching to verify the top result actually matches the
        provided title (threshold: {threshold}).

        Args:
            title: Article title to search
            author_last: Last name of first author (improves precision)

        Returns:
            Normalized metadata dict or None if no confident match
        """
        # Build cache key
        cache_key = f"search:{title.lower()[:80]}:{(author_last or '').lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        params: Dict = {
            'query.title': title,
            'rows': 5,
            'select': 'DOI,title,author,container-title,volume,issue,page,issued,URL,abstract,publisher',
        }
        if author_last:
            params['query.author'] = author_last

        data = self._get(CROSSREF_SEARCH_URL, params=params)
        if not data or data.get('status') != 'ok':
            self._cache[cache_key] = None
            _save_cache(self._cache)
            return None

        items = data.get('message', {}).get('items', [])
        for item in items:
            item_titles = item.get('title', [])
            if not item_titles:
                continue
            candidate_title = item_titles[0]
            ratio = SequenceMatcher(None, title.lower(), candidate_title.lower()).ratio()
            if ratio >= FUZZY_MATCH_THRESHOLD:
                normalized = _normalize_message(item)
                self._cache[cache_key] = normalized
                _save_cache(self._cache)
                return normalized

        # No confident match
        self._cache[cache_key] = None
        _save_cache(self._cache)
        return None
