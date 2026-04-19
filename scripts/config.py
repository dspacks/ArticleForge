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
