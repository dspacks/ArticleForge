"""
Configuration for ArticleForge Article Processing System
"""

import os
from pathlib import Path

# Base paths - adjust relative to script location
BASE_DIR = Path(__file__).parent.parent
INTAKE_DIR = BASE_DIR / "intake"
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "pdf_archive"
METADATA_DIR = BASE_DIR / "metadata"

# Metadata registry file
METADATA_REGISTRY = METADATA_DIR / "articles_metadata.json"

# CrossRef API cache
CROSSREF_CACHE = METADATA_DIR / ".crossref_cache.json"

# Schema versioning
METADATA_SCHEMA_VERSION = 2

# Schema definition for version 2
# New fields added in v2 (all optional for backward compat):
#   authors         - List[Dict] with {first, last, full, affiliation}
#   publication     - Dict with {journal, volume, issue, pages}
#   doi             - str DOI (e.g. "10.1000/xyz123")
#   url             - str URL
#   abstract        - str abstract text
#   pdf_archive_path - str path to archived PDF
#   extraction_confidence - Dict[field -> float 0.0-1.0]
#   extraction_sources    - Dict[field -> str source name]
#   schema_version  - int (1 = legacy, 2 = current)
#
# Legacy fields kept for backward compat:
#   author          - str (legacy; synthesized from authors[].full joined '; ')
METADATA_SCHEMA_V2_FIELDS = [
    "authors",
    "publication",
    "doi",
    "url",
    "abstract",
    "pdf_archive_path",
    "extraction_confidence",
    "extraction_sources",
    "schema_version",
]

# Processing settings
MIN_KEYWORDS = 3
MAX_KEYWORDS = 8
KEYWORD_STRATEGY = "tfidf"  # tfidf or simple
DATE_FORMATS = [
    "%B %d, %Y",
    "%m/%d/%Y",
    "%Y-%m-%d",
    "%d-%m-%Y",
]

# Stop words for keyword extraction
COMMON_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that',
    'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what',
    'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
    'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
    'not', 'only', 'same', 'so', 'than', 'too', 'very', 'just'
}

# Ensure directories exist
for dir_path in [INTAKE_DIR, OUTPUT_DIR, ARCHIVE_DIR, METADATA_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
