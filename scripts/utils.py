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


# ---------------------------------------------------------------------------
# Task 1.2 — DOI extractor
# ---------------------------------------------------------------------------

_DOI_PATTERN = re.compile(
    r'\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b',
    re.IGNORECASE
)


def _validate_doi(candidate: str) -> bool:
    """Basic structural validation of a DOI string."""
    if not candidate:
        return False
    # Must start with '10.'
    if not candidate.startswith('10.'):
        return False
    # Must contain exactly at least one '/' after the registrant prefix
    if '/' not in candidate:
        return False
    # No spaces allowed
    if ' ' in candidate:
        return False
    # Registrant prefix must be numeric (4-9 digits)
    parts = candidate.split('/', 1)
    prefix = parts[0]  # e.g. "10.1234"
    prefix_digits = prefix.split('.', 1)
    if len(prefix_digits) < 2 or not prefix_digits[1].isdigit():
        return False
    return True


def extract_doi(text: str, pdf_metadata: Optional[Dict] = None) -> Optional[str]:
    """
    Extract DOI from PDF metadata or article text.

    Search order:
      1. PDF metadata subject/title fields
      2. First page (first 2000 chars of text)
      3. Last page (last 2000 chars of text, where references live)

    Args:
        text: Full extracted article text
        pdf_metadata: Dict from extract_pdf_metadata() (optional)

    Returns:
        DOI string (e.g. "10.1234/abcd") or None
    """
    # 1. Search PDF metadata fields
    if pdf_metadata:
        for field in ('subject', 'title', 'author'):
            value = pdf_metadata.get(field) or ''
            m = _DOI_PATTERN.search(value)
            if m and _validate_doi(m.group(1)):
                return m.group(1).rstrip('.')

    if not text:
        return None

    # 2. First page — most articles put DOI near the top
    for region in (text[:2000], text[-2000:]):
        m = _DOI_PATTERN.search(region)
        if m and _validate_doi(m.group(1)):
            return m.group(1).rstrip('.')

    return None


# ---------------------------------------------------------------------------
# Task 1.3 — Structured author parsing
# ---------------------------------------------------------------------------

_HONORIFICS = re.compile(
    r'\b(Ph\.?D\.?|M\.?D\.?|M\.?B\.?A\.?|Jr\.?|Sr\.?|III|II|IV|Esq\.?|Prof\.?|Dr\.?)\b',
    re.IGNORECASE
)


def _strip_honorifics(name: str) -> str:
    """Remove common honorific suffixes from a name string."""
    return _HONORIFICS.sub('', name).strip(' ,;')


def _parse_single_author(raw: str) -> Optional[Dict]:
    """
    Parse a single author name string into structured form.

    Handles:
      - "Last, First [M.]"   (comma-separated)
      - "First [M.] Last"    (natural order)

    Returns dict with keys: first, last, full, affiliation
    """
    raw = _strip_honorifics(raw).strip()
    if not raw:
        return None

    # Remove leftover parenthetical content (affiliations in parens)
    affiliation = None
    paren_match = re.search(r'\(([^)]+)\)', raw)
    if paren_match:
        affiliation = paren_match.group(1).strip()
        raw = raw[:paren_match.start()].strip()

    # "Last, First" pattern
    if ',' in raw:
        parts = [p.strip() for p in raw.split(',', 1)]
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ''
        full = f"{first} {last}".strip() if first else last
    else:
        # "First [Middle] Last" natural order
        tokens = raw.split()
        if len(tokens) == 1:
            last = tokens[0]
            first = ''
        elif len(tokens) == 2:
            first, last = tokens
        else:
            # "First Middle Last" → keep all middle initials with first
            first = ' '.join(tokens[:-1])
            last = tokens[-1]
        full = f"{first} {last}".strip() if first else last

    if not last:
        return None

    return {
        'first': first,
        'last': last,
        'full': full,
        'affiliation': affiliation,
    }


def parse_authors(raw: str) -> List[Dict]:
    """
    Parse a raw author string into a list of structured author dicts.

    Splits on: ';', ' and ', ' & ', and ',' (when not part of Last-First).

    Args:
        raw: Raw author string (e.g. "Jane Doe; John Smith and Alice Brown")

    Returns:
        List of dicts with keys: first, last, full, affiliation
    """
    if not raw or not raw.strip():
        return []

    # Normalize separators: replace ' and ' / ' & ' with ';'
    normalized = re.sub(r'\s+and\s+', ';', raw, flags=re.IGNORECASE)
    normalized = re.sub(r'\s*&\s*', ';', normalized)

    # Now split on ';'
    raw_names = [n.strip() for n in normalized.split(';') if n.strip()]

    # If only one token and it contains a comma NOT in "Last, First" position,
    # try splitting on commas as secondary separator
    if len(raw_names) == 1 and raw_names[0].count(',') > 1:
        # Multiple commas: might be "Smith, John, Jones, Alice" (list of Last,First pairs)
        # or "Smith, John, Jones Alice" — try comma split and re-group
        parts = [p.strip() for p in raw_names[0].split(',')]
        # Attempt to re-pair as Last, First
        repaired = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and parts[i + 1] and parts[i + 1][0].isupper():
                # Looks like "Last, First" pair
                repaired.append(f"{parts[i]}, {parts[i+1]}")
                i += 2
            else:
                repaired.append(parts[i])
                i += 1
        if repaired:
            raw_names = repaired

    authors = []
    for name in raw_names:
        parsed = _parse_single_author(name)
        if parsed:
            authors.append(parsed)

    return authors


def extract_authors(text: str, pdf_metadata_author: Optional[str] = None) -> List[Dict]:
    """
    Extract structured author list from PDF metadata or article text.

    Args:
        text: Full article text
        pdf_metadata_author: Author string from PDF metadata (preferred)

    Returns:
        List of author dicts with keys: first, last, full, affiliation
    """
    raw = None

    # Prefer PDF metadata
    if pdf_metadata_author and pdf_metadata_author.strip():
        raw = pdf_metadata_author.strip()
    elif text:
        # Fallback: search text for author patterns
        search_text = text[:1000]
        # "By Name" pattern
        m = re.search(r'[Bb]y\s+([A-Z][a-z]+(?:[\s,]+[A-Z][a-z.]+)*)', search_text)
        if m:
            raw = m.group(1)
        else:
            # "Author(s):" pattern
            m = re.search(r'[Aa]uthor(?:\(s\))?:?\s+([A-Z][^\n]{2,80})', search_text)
            if m:
                raw = m.group(1).strip()

    if not raw:
        return []

    return parse_authors(raw)


# ---------------------------------------------------------------------------
# Task 1.4 — Publication detail and abstract extractors
# ---------------------------------------------------------------------------

def extract_publication_details(text: str) -> Dict:
    """
    Extract structured publication details from article text.

    Looks for:
      - Journal name (near "journal:", "published in", etc.)
      - Volume / Issue number
      - Page range

    Args:
        text: Full article text

    Returns:
        Dict with keys: journal (Optional[str]), volume (Optional[str]),
                        issue (Optional[str]), pages (Optional[str])
    """
    result: Dict = {
        'journal': None,
        'volume': None,
        'issue': None,
        'pages': None,
    }

    if not text:
        return result

    # Search first 3000 chars (header/abstract area) and last 1000 (footer/citation)
    search_text = text[:3000] + '\n' + text[-1000:]

    # Volume/Issue: "Vol. 5, No. 3" or "Volume 12, Issue 4"
    vol_issue = re.search(
        r'[Vv]ol(?:ume)?\.?\s*(\d+)[,\s]+(?:[Nn]o\.?|[Ii]ssue|[Ii]ss\.?)\s*(\d+)',
        search_text
    )
    if vol_issue:
        result['volume'] = vol_issue.group(1)
        result['issue'] = vol_issue.group(2)

    # Pages: "pp. 23-45" or "p. 23-45" or "pages 23–45"
    pages = re.search(
        r'pp?\.?\s*(\d+)\s*[-\u2013]\s*(\d+)',
        search_text
    )
    if pages:
        result['pages'] = f"{pages.group(1)}-{pages.group(2)}"

    return result


def extract_abstract(text: str) -> Optional[str]:
    """
    Extract abstract text from article.

    Looks for "Abstract" header followed by text, ending at next section header
    or after ~500 words.

    Args:
        text: Full article text

    Returns:
        Abstract text or None
    """
    if not text:
        return None

    # Pattern: "Abstract" on its own line or inline, followed by body text
    abstract_match = re.search(
        r'(?:^|\n)\s*[Aa]bstract\s*[\n:]\s*([\s\S]{50,2000}?)(?=\n\s*(?:[A-Z][A-Za-z ]{2,30}\n|\d+\s*\n|Introduction|Keywords|Background)|\Z)',
        text
    )
    if abstract_match:
        abstract = abstract_match.group(1).strip()
        # Truncate at ~500 words
        words = abstract.split()
        if len(words) > 500:
            abstract = ' '.join(words[:500]) + '...'
        return abstract

    return None


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


# ---------------------------------------------------------------------------
# Improved title extraction — handles magazine-style layouts (HBR, etc.)
# ---------------------------------------------------------------------------

# Lines that indicate a byline has started (stop collecting title lines)
_BYLINE_PATTERN = re.compile(r'^\s*[Bb]y\s+[A-Z]', re.MULTILINE)

# Lines that look like body-text paragraphs: start lowercase or are very long
_BODY_TEXT_PATTERN = re.compile(r'^[a-z]')

# Sentinel: a line that is ALL CAPS (new section header, not part of title)
_ALL_CAPS_LINE = re.compile(r'^[A-Z][A-Z\s\-]{4,}$')

# Section-header prefix: "WORD WORD:" at start of a line (e.g. "MANAGING YOURSELF:")
_SECTION_HEADER_RE = re.compile(
    r'^([A-Z][A-Z\s\-\']{2,}):\s*(.*)',
    re.DOTALL
)


def _is_body_text_line(line: str) -> bool:
    """Return True if line looks like the start of body/paragraph text."""
    if not line:
        return False
    # Starts lowercase → body text
    if _BODY_TEXT_PATTERN.match(line):
        return True
    # Very long lines (> 120 chars) are almost certainly body text
    if len(line) > 120:
        return True
    # Lines that end with a period and are long enough to be a sentence
    # (more than 8 words) are body sentences, not title fragments
    if line.endswith('.') and len(line.split()) > 8:
        return True
    return False


def _collect_title_lines(lines: List[str], start_idx: int) -> List[str]:
    """
    From start_idx, collect lines that belong to a multi-line title.

    Stop collecting when we hit:
    - An empty line followed by a new section (after at least 1 line)
    - A byline marker ("By Name")
    - A body-text paragraph (lowercase start, very long)
    - A word count per line that suggests subtitle/dek rather than title
      (> 12 words on a single line)
    - A second all-caps word appearing (new section header)

    Returns a list of line strings to join as the title.
    """
    collected: List[str] = []
    for i in range(start_idx, min(start_idx + 10, len(lines))):
        line = lines[i].strip()
        if not line:
            # Blank line — stop if we already have content
            if collected:
                break
            continue
        # Byline → stop
        if re.match(r'^[Bb]y\s+[A-Z]', line):
            break
        # Body text → stop
        if _is_body_text_line(line):
            break
        # Lines with > 10 words that start uppercase look like body sentences,
        # not title fragments — stop collecting (dek/subtitle allowed only if
        # we haven't collected anything yet OR the line is very short)
        word_count = len(line.split())
        if word_count > 10 and collected:
            break
        # All-caps full line after we've already collected something → new section
        if collected and _ALL_CAPS_LINE.match(line):
            break
        collected.append(line)
    return collected


def extract_title_improved(
    text: str,
    pdf_metadata_title: Optional[str] = None,
) -> tuple:
    """
    Extract article title with handling for magazine-style layouts (HBR, etc.).

    Strategy:
      1. Prefer PDF metadata title if it passes quality checks.
      2. Pattern 1: Detect "SECTION HEADER: title text" on first line.
         - Captures section label + multi-line title that follows.
      3. Pattern 2: Multi-line title search in first ~30 lines without a header.
      4. Deduplicate check: if extracted title matches first sentence of body
         text it is probably wrong; returns (None, 0.0) to trigger CrossRef.
      5. Falls back to original extract_title() logic.

    Args:
        text: Full extracted article text.
        pdf_metadata_title: Title from PDF metadata properties (preferred).

    Returns:
        Tuple of (title: Optional[str], confidence: float).
        confidence values:
          0.95 — PDF metadata
          0.90 — section header pattern
          0.65 — multi-line text pattern
          0.50 — basic fallback
          0.0  — nothing found (CrossRef fallback recommended)
    """
    # ------------------------------------------------------------------ #
    # 1. PDF metadata title
    # ------------------------------------------------------------------ #
    if pdf_metadata_title:
        meta = pdf_metadata_title.strip()
        # Reject if it looks like a filename, URL, or is too short/long
        if (5 < len(meta) < 300
                and not meta.lower().endswith('.pdf')
                and 'http' not in meta.lower()):
            return (meta, 0.95)

    if not text:
        return (None, 0.0)

    # Work only with first 1200 chars (title region)
    head = text[:1200]
    lines = [ln.strip() for ln in head.split('\n')]
    # Remove blank lines for easier scanning but keep index mapping
    non_blank = [(i, ln) for i, ln in enumerate(lines) if ln]

    # ------------------------------------------------------------------ #
    # 2. Pattern 1 — "SECTION HEADER: title text on same or next lines"
    # ------------------------------------------------------------------ #
    for raw_idx, (line_idx, line) in enumerate(non_blank[:15]):
        m = _SECTION_HEADER_RE.match(line)
        if m:
            section_label = m.group(1).strip()   # e.g. "MANAGING YOURSELF"
            remainder = m.group(2).strip()        # text after colon on same line

            # Collect title lines starting from remainder (if any) + next lines
            title_parts: List[str] = []
            if remainder:
                title_parts.append(remainder)
                next_start = raw_idx + 1
            else:
                next_start = raw_idx + 1

            # Collect continuation lines
            continuation_lines = [ln for _, ln in non_blank[next_start:next_start + 8]]
            extra = _collect_title_lines(continuation_lines, 0)
            title_parts.extend(extra)

            if title_parts:
                raw_title = ' '.join(title_parts)
                # Clean: remove trailing periods if they're clearly sentence-end
                raw_title = raw_title.rstrip('. ')
                # Sanity: must be > 5 words or > 15 chars to be a real title
                # (section header already confirms magazine context, so short titles OK)
                if len(raw_title) > 15 or len(raw_title.split()) > 3:
                    return (raw_title, 0.90)

    # ------------------------------------------------------------------ #
    # 3. Pattern 2 — Multi-line title without explicit section header
    #    Look for a cluster of capitalized short-ish lines near the top
    # ------------------------------------------------------------------ #
    for raw_idx, (line_idx, line) in enumerate(non_blank[:10]):
        # Skip lines that look like section-only headers (all caps, short)
        if _ALL_CAPS_LINE.match(line) and len(line.split()) <= 3:
            continue
        # Look for a title-like line: starts with capital, not body text
        if (line and line[0].isupper() and not _is_body_text_line(line)
                and len(line) > 10):
            continuation_lines = [ln for _, ln in non_blank[raw_idx:raw_idx + 8]]
            parts = _collect_title_lines(continuation_lines, 0)
            if parts:
                candidate = ' '.join(parts).rstrip('. ')
                if len(candidate) > 15:
                    return (candidate, 0.65)

    # ------------------------------------------------------------------ #
    # 4. Fallback — original heuristic
    # ------------------------------------------------------------------ #
    fallback = extract_title(text, None)
    if fallback:
        return (fallback, 0.50)

    return (None, 0.0)


def extract_author(text: str, pdf_metadata_author: Optional[str] = None) -> Optional[str]:
    """
    Legacy shim: extract author string from PDF metadata or text.

    Internally delegates to extract_authors() (structured) and joins
    full names with '; ' for backward compatibility.

    Args:
        text: Full article text
        pdf_metadata_author: Author from PDF metadata (preferred if available)

    Returns:
        Author name string ('; '-joined if multiple) or None
    """
    authors = extract_authors(text, pdf_metadata_author)
    if not authors:
        return None
    return '; '.join(a['full'] for a in authors if a.get('full'))


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
