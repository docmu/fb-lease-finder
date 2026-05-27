import re
from dataclasses import dataclass, field
from config import BATHROOM_KEYWORDS, LOCATION_KEYWORDS, EXCLUDE_KEYWORDS


# Broad August match used for the must-match check
_AUGUST_RE = re.compile(r'\baug(?:ust)?\.?\b|8/\d{1,2}', re.IGNORECASE)

# Specific date extraction: "Aug 1", "August 15th", "8/1", etc.
_DATE_EXTRACT_RE = re.compile(
    r'8/\d{1,2}|aug(?:ust)?\.?\s*\d{1,2}(?:st|nd|rd|th)?',
    re.IGNORECASE,
)

_NUM = r'(?:\d+|one|two|three)'
_BEDS_RE = re.compile(rf'({_NUM})\s*(?:bed(?:room)?s?|bdrm|br|bd)\b', re.IGNORECASE)
_BATHS_RE = re.compile(rf'({_NUM})\s*(?:bath(?:room)?s?|ba|bth|br)\b', re.IGNORECASE)

# Detects short-term sublet date ranges involving August:
#   cross-month: "June - August", "June 1 - August 1", "June to August"
#   within-August: "August 2-5", "Aug 1 - 15"
_RANGE_TO_AUG_RE = re.compile(
    r'(?:'
    r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?)'
    r'.{1,50}?(?:[-–—]|\bto\b|\bthrough\b|\buntil\b)\s*\baug(?:ust)?\b'
    r'|'
    r'\baug(?:ust)?\.?\s*\d{1,2}\s*[-–—]\s*(?:\baug(?:ust)?\.?\s*)?\d{1,2}\b'
    r')',
    re.IGNORECASE,
)
_TAKEOVER_RE = re.compile(r'\b(?:(?:lease\s+)?takeover(?:\s+lease)?|re[-\s]?sign)\b', re.IGNORECASE)


@dataclass
class Post:
    text: str
    url: str
    timestamp: str
    source_group: str = ""
    posted_at: int = 0  # Unix timestamp from data-utime; 0 means unknown
    matched_terms: list[str] = field(default_factory=list)
    # Structured display fields populated by evaluate()
    move_in_date: str = ""
    neighborhood: str = ""
    beds_baths: str = ""


def _any_match(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw in lower]


def _extract_move_in_date(text: str) -> str:
    m = _DATE_EXTRACT_RE.search(text)
    return m.group(0).strip() if m else ""


def _extract_neighborhood(location_hits: list[str]) -> str:
    if not location_hits:
        return ""
    return max(location_hits, key=len).strip().title()


def _extract_beds_baths(text: str) -> str:
    beds_m = _BEDS_RE.search(text)
    baths_m = _BATHS_RE.search(text)
    parts = []
    if beds_m:
        parts.append(f"{beds_m.group(1)} bed")
    if baths_m:
        parts.append(f"{baths_m.group(1)} bath")
    return " / ".join(parts)


def evaluate(post: Post) -> bool:
    """Return True if post matches all criteria and contains no excluded terms."""
    lower = post.text.lower()

    if any(kw in lower for kw in EXCLUDE_KEYWORDS):
        return False

    # Drop short-term sublets (e.g. June - August) unless it's a lease takeover/re-sign
    if _RANGE_TO_AUG_RE.search(post.text) and not _TAKEOVER_RE.search(post.text):
        return False

    move_in_hits = _AUGUST_RE.findall(post.text)
    bathroom_hits = _any_match(post.text, BATHROOM_KEYWORDS)
    location_hits = _any_match(post.text, LOCATION_KEYWORDS)

    post.matched_terms = move_in_hits + bathroom_hits + location_hits

    if not (move_in_hits and bathroom_hits and location_hits):
        return False

    post.move_in_date = _extract_move_in_date(post.text)
    post.neighborhood = _extract_neighborhood(location_hits)
    post.beds_baths = _extract_beds_baths(post.text)

    return True
