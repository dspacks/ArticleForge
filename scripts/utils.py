"""
Utility functions for PDF processing and text extraction
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from collections import Counter
import string

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: pytesseract/PIL not available. OCR will be skipped.")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("Warning: pdfplumber not available. PDF text extraction may fail.")

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("Warning: PyPDF2 not available. PDF metadata extraction will be skipped.")

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("Warning: pdf2image not available. OCR fallback unavailable.")

from config import COMMON_STOPWORDS, DATE_FORMATS


def extract_pdf_metadata(pdf_path: Path) -> Dict[str, Optional[str]]:
    """
    Extract metadata (title, author, subject, creation date) from PDF properties.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with title, author, date, subject fields (all may be None)
    """
    metadata = {
        'title': None,
        'author': None,
        'date': None,
        'subject': None,
    }

    if not PYPDF2_AVAILABLE:
        return metadata

    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            doc_metadata = reader.metadata

            if doc_metadata:
                # Extract title - try multiple field names
                if '/Title' in doc_metadata:
                    title = doc_metadata['/Title']
                    if isinstance(title, bytes):
                        title = title.decode('utf-8', errors='ignore')
                    if title and title.strip():
                        metadata['title'] = title.strip()

                # Extract author
                if '/Author' in doc_metadata:
                    author = doc_metadata['/Author']
                    if isinstance(author, bytes):
                        author = author.decode('utf-8', errors='ignore')
                    if author and author.strip():
                        metadata['author'] = author.strip()

                # Extract subject
                if '/Subject' in doc_metadata:
                    subject = doc_metadata['/Subject']
                    if isinstance(subject, bytes):
                        subject = subject.decode('utf-8', errors='ignore')
                    if subject and subject.strip():
                        metadata['subject'] = subject.strip()

                # Extract creation date
                if '/CreationDate' in doc_metadata:
                    date_str = doc_metadata['/CreationDate']
                    if isinstance(date_str, bytes):
                        date_str = date_str.decode('utf-8', errors='ignore')
                    # Parse PDF date format: D:YYYYMMDDHHmmSS
                    if date_str and date_str.startswith('D:'):
                        try:
                            date_part = date_str[2:10]  # Extract YYYYMMDD
                            year = date_part[0:4]
                            month = date_part[4:6]
                            day = date_part[6:8]
                            metadata['date'] = f"{year}-{month}-{day}"
                        except (ValueError, IndexError):
                            pass

    except Exception as e:
        print(f"    Warning: Could not extract PDF metadata: {e}")

    return metadata


def extract_text_from_pdf(pdf_path: Path, use_layout_mode: bool = True) -> str:
    """
    Extract text from PDF using pdfplumber with layout-aware extraction.

    This uses pdfplumber's layout-mode which better handles multi-column layouts,
    tables, and preserves spatial relationships between text elements.

    Args:
        pdf_path: Path to PDF file
        use_layout_mode: If True, uses layout-aware extraction (better for formatted PDFs)

    Returns:
        Extracted text
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber is required. Install with: pip install pdfplumber")

    text = ""

    # Try layout-aware extraction first (better for multi-column ArticleForge PDFs)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Use layout mode for better structure preservation
                if use_layout_mode:
                    page_text = page.extract_text(layout=True)
                else:
                    page_text = page.extract_text()

                if page_text:
                    # Add page break marker for clarity
                    text += page_text + "\n[PAGE BREAK]\n"
    except Exception as e:
        print(f"  Error in layout-aware extraction for {pdf_path.name}: {e}")
        # Fallback to standard extraction
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e2:
            print(f"  Error in fallback extraction: {e2}")

    # Clean up extracted text
    text = clean_extracted_text(text)

    # If minimal text extracted, try OCR
    if len(text.strip()) < 100 and TESSERACT_AVAILABLE and PDF2IMAGE_AVAILABLE:
        print(f"  Text sparse, attempting OCR on {pdf_path.name}...")
        try:
            images = pdf2image.convert_from_path(str(pdf_path))
            for image in images:
                ocr_text = pytesseract.image_to_string(image)
                if ocr_text:
                    text += ocr_text + "\n"
        except Exception as e:
            print(f"  OCR fallback failed: {e}")

    return text.strip()


def clean_extracted_text(text: str) -> str:
    """
    Clean up extracted PDF text to remove formatting artifacts and improve readability.

    This function:
    - Removes excessive whitespace
    - Fixes merged words (e.g., "areideaWatch" → "are ideaWatch")
    - Preserves paragraph structure
    - Removes page break markers
    - Separates tables and sidebars
    - Normalizes line endings

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text
    """
    if not text:
        return text

    lines = text.split('\n')
    cleaned_lines = []
    in_table_section = False

    for i, line in enumerate(lines):
        # Skip page break markers
        if '[PAGE BREAK]' in line:
            cleaned_lines.append('')  # Empty line as separator
            continue

        # Remove excessive leading/trailing whitespace
        line = line.strip()

        if not line:
            continue

        # Detect and separate table/sidebar content (heuristics)
        is_table_like = detect_table_or_sidebar_line(line, i, lines)

        if is_table_like:
            # Add visual separator before table/sidebar content
            if not in_table_section and cleaned_lines:
                cleaned_lines.append('\n--- TABLE/SIDEBAR DATA ---\n')
                in_table_section = True
            cleaned_lines.append(line)
            continue
        else:
            if in_table_section:
                in_table_section = False

        # Fix common merged word patterns (e.g., "areideaWatch" → "are ideaWatch")
        # Insert space before all-caps words in the middle of text
        line = re.sub(r'([a-z])([A-Z]{2,})', r'\1 \2', line)

        # Insert space before capitalized words that follow lowercase (camelCase split)
        line = re.sub(r'([a-z]{2,})([A-Z][a-z]+)', r'\1 \2', line)

        # Fix hyphens at line ends that shouldn't be there
        if line.endswith('-') and len(line) > 1:
            # Check if this looks like a hyphenated word break
            if not line[-2].isupper():  # Not like "A-", "WORD-"
                line = line[:-1]  # Remove trailing hyphen

        # Normalize multiple spaces to single space
        line = re.sub(r' {2,}', ' ', line)

        cleaned_lines.append(line)

    # Join lines, preserving paragraph structure
    text = '\n'.join(cleaned_lines)

    # Remove multiple consecutive blank lines (keep max 2)
    text = re.sub(r'\n\n\n+', '\n\n', text)

    return text.strip()


def detect_table_or_sidebar_line(line: str, line_idx: int, all_lines: List[str]) -> bool:
    """
    Detect if a line is part of a table or sidebar (heuristics).

    Signs of table/sidebar content:
    - Very short lines (< 20 chars)
    - All UPPERCASE with numbers
    - Appears to be data (numbers, currency, etc.)
    - Sidebar-like formatting

    Args:
        line: The line to check
        line_idx: Index of line in full text
        all_lines: All lines (for context)

    Returns:
        True if line appears to be table/sidebar content
    """
    # Skip if line is too long to be sidebar/table
    if len(line) > 80:
        return False

    # Check for table indicators
    # All uppercase + short = likely a header or short cell
    if line.isupper() and len(line) < 30:
        return True

    # Numbers + special chars = likely table data
    if re.search(r'\d+\s+\d+|\d+\s*%|\$\d+', line):
        return True

    # All caps with numbers and short length
    if len(line) < 25 and any(c.isdigit() for c in line) and sum(1 for c in line if c.isupper()) > len(line) / 2:
        return True

    # Very short lines in sequence might be sidebar
    if len(line) < 15 and line_idx > 0:
        # Check if previous line was also short (sidebar pattern)
        prev_line = all_lines[line_idx - 1].strip() if line_idx > 0 else ""
        if 0 < len(prev_line) < 30 and prev_line.isupper():
            return True

    # Lines that look like author/affiliation info
    if re.match(r'^(Professor|Author|By|Editor|Ph\.D\.)', line):
        return True

    # "SOURCE:", "ABOUT THE", etc. markers
    if re.match(r'^(SOURCE|ABOUT|NOTE|DATA)[\s:]', line, re.IGNORECASE):
        return True

    return False


def extract_title(text: str, pdf_metadata_title: Optional[str] = None) -> Optional[str]:
    """
    Extract article title from text or PDF metadata.

    Args:
        text: Full article text
        pdf_metadata_title: Title from PDF metadata (preferred if available)

    Returns:
        Title or None
    """
    # Prefer PDF metadata if available and looks like a real title
    if pdf_metadata_title and len(pdf_metadata_title) > 5 and len(pdf_metadata_title) < 300:
        return pdf_metadata_title

    if not text:
        return None

    # Fallback: extract from text
    first_part = text[:500]
    lines = [line.strip() for line in first_part.split('\n') if line.strip()]

    for line in lines[:10]:
        if (len(line) > 20 and
            len(line) < 200 and
            line[0].isupper() and
            not line.isupper()):
            return line

    return None


def extract_author(text: str, pdf_metadata_author: Optional[str] = None) -> Optional[str]:
    """
    Extract author from PDF metadata or text using common patterns.

    Args:
        text: Full article text
        pdf_metadata_author: Author from PDF metadata (preferred if available)

    Returns:
        Author name or None
    """
    # Prefer PDF metadata if available
    if pdf_metadata_author and pdf_metadata_author.strip():
        return pdf_metadata_author.strip()

    if not text:
        return None

    # Fallback: search in text
    search_text = text[:1000]

    # Pattern 1: "By Name"
    match = re.search(r'[Bb]y\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', search_text)
    if match:
        return match.group(1)

    # Pattern 2: "Author: Name" or "Author(s):"
    match = re.search(r'[Aa]uthor(?:\(s\))?:?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', search_text)
    if match:
        return match.group(1)

    # Pattern 3: Multiple author pattern
    match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*and\s+([A-Z][a-z]+)', search_text)
    if match:
        return f"{match.group(1)} and {match.group(2)}"

    return None


def extract_date(text: str, pdf_metadata_date: Optional[str] = None) -> Optional[str]:
    """
    Extract publication date from PDF metadata or text.

    Args:
        text: Full article text
        pdf_metadata_date: Date from PDF metadata in YYYY-MM-DD format (preferred)

    Returns:
        Formatted date string (YYYY-MM-DD) or None
    """
    # Prefer PDF metadata if available and looks like a valid date
    if pdf_metadata_date and re.match(r'\d{4}-\d{2}-\d{2}', pdf_metadata_date):
        return pdf_metadata_date

    if not text:
        return None

    search_text = text[:1000]

    # Try each date format
    for pattern in DATE_FORMATS:
        try:
            if pattern == "%B %d, %Y":
                match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', search_text)
                if match:
                    date_str = f"{match.group(1)} {match.group(2)}, {match.group(3)}"
                    date_obj = datetime.strptime(date_str, pattern)
                    return date_obj.strftime("%Y-%m-%d")

            elif pattern == "%m/%d/%Y":
                match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', search_text)
                if match:
                    date_str = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
                    date_obj = datetime.strptime(date_str, pattern)
                    return date_obj.strftime("%Y-%m-%d")

            elif pattern == "%Y-%m-%d":
                match = re.search(r'(\d{4})-(\d{2})-(\d{2})', search_text)
                if match:
                    return match.group(0)
        except (ValueError, AttributeError):
            continue

    return None


def extract_keywords(text: str, num_keywords: int = 5) -> List[str]:
    """
    Extract keywords using TF-IDF-like approach (term frequency with stopword removal).

    Args:
        text: Full article text
        num_keywords: Number of keywords to extract

    Returns:
        List of keyword strings
    """
    if not text:
        return []

    # Normalize text
    text = text.lower()

    # Remove punctuation but keep hyphens for hyphenated words
    text = re.sub(r'[^\w\s\-]', ' ', text)

    # Split into words
    words = text.split()

    # Filter: remove stopwords, short words, numbers, and duplicates
    filtered_words = [
        word.strip('-') for word in words
        if (word.lower() not in COMMON_STOPWORDS and
            len(word) > 3 and
            not word.isdigit() and
            not word.startswith('-') and
            not word.endswith('-'))
    ]

    # Count frequency
    word_freq = Counter(filtered_words)

    # Get top keywords
    keywords = [word for word, _ in word_freq.most_common(num_keywords)]

    return sorted(keywords)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '', filename)

    # Remove multiple spaces and trailing dots
    sanitized = re.sub(r'\s+', ' ', sanitized).strip('. ')

    return sanitized


def create_markdown_content(
    title: str,
    author: Optional[str],
    date: Optional[str],
    keywords: List[str],
    text: str,
    source: Optional[str] = None
) -> str:
    """
    Create markdown content with YAML frontmatter.

    Args:
        title: Article title
        author: Author name
        date: Publication date (YYYY-MM-DD)
        keywords: List of keywords/tags
        text: Full article text
        source: Publication/source name (e.g., ArticleForge, WSJ)

    Returns:
        Formatted markdown string
    """
    # Build YAML frontmatter
    frontmatter = ["---"]
    frontmatter.append(f"title: {title}")

    if author:
        frontmatter.append(f"author: {author}")

    if date:
        frontmatter.append(f"date: {date}")

    if source:
        frontmatter.append(f"source: {source}")

    if keywords:
        keywords_str = ", ".join(keywords)
        frontmatter.append(f"keywords: [{keywords_str}]")

    frontmatter.append(f"processed: {datetime.now().strftime('%Y-%m-%d')}")
    frontmatter.append("---\n")

    # Combine frontmatter with text
    markdown = "\n".join(frontmatter) + text

    return markdown


def extract_publication(text: str) -> Optional[str]:
    """
    Extract publication/journal name from article text.

    Looks for common publication markers in the first 1000 characters.

    Args:
        text: Article text

    Returns:
        Publication name or None
    """
    if not text:
        return None

    search_text = text[:1500].lower()

    # Check for specific publications
    publication_markers = {
        'harvard business review': 'ArticleForge',
        'hbr.org': 'ArticleForge',
        'harvard business': 'ArticleForge',
        'wall street journal': 'WSJ',
        'financial times': 'FT',
        'forbes': 'Forbes',
        'mckinsey': 'McKinsey',
        'bain & company': 'Bain',
    }

    for marker, publication in publication_markers.items():
        if marker in search_text:
            return publication

    return None


def parse_metadata_from_filename(pdf_filename: str) -> Dict[str, str]:
    """
    Extract any metadata from the PDF filename itself (useful for EBSCO exports).

    Args:
        pdf_filename: The PDF filename

    Returns:
        Dictionary with any extracted metadata
    """
    metadata = {}

    # EBSCO filename pattern: EBSCO-FullText-MM_DD_YYYY (N).pdf
    match = re.match(r'EBSCO-FullText-(\d{2})_(\d{2})_(\d{4})', pdf_filename)
    if match:
        month, day, year = match.groups()
        # Default to EBSCO, but will be overridden by actual publication if found
        metadata['source'] = 'EBSCO'
        metadata['export_date'] = f"{year}-{month}-{day}"

    return metadata
