import re
from dataclasses import dataclass, field
from config import BATHROOM_KEYWORDS, LOCATION_KEYWORDS, EXCLUDE_KEYWORDS


# Broad move-in month match used for the must-match check
_MOVE_IN_MONTH_RE = re.compile(r'\bjul(?:y)?\.?\b|7/\d{1,2}', re.IGNORECASE)

# Specific date extraction: "Jul 1", "July 15th", "7/1", etc.
_DATE_EXTRACT_RE = re.compile(
    r'7/\d{1,2}|jul(?:y)?\.?\s*\d{1,2}(?:st|nd|rd|th)?',
    re.IGNORECASE,
)

_NUM = r'(?:\d+|one|two|three)'
_BEDS_RE = re.compile(rf'({_NUM})\s*(?:bed(?:room)?s?|bdrm|br|bd)\b', re.IGNORECASE)
_BATHS_RE = re.compile(rf'({_NUM})\s*(?:bath(?:room)?s?|ba|bth|br)\b', re.IGNORECASE)

# Detects short-term sublet date ranges involving move in month:
#   ending in July:    "June - July", "June 1 - July 1", "June to July"
#   starting in July:  "July - September", "July to August"
#   within July:       "July 2-5", "Jul 1st - 31st", "July 1st-July 31st"
_MONTHS = r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
_SEP = r'(?:[-–—]|\bto\b|\bthrough\b|\buntil\b)'
_ORD = r'(?:st|nd|rd|th)?'
_SHORT_TERM_SUBLET_RANGE_RE = re.compile(
    rf'(?:'
    rf'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?)'
    rf'.{{1,50}}?{_SEP}\s*\bjul(?:y)?\b'
    rf'|'
    rf'\bjul(?:y)?\b.{{0,20}}?{_SEP}\s*\b{_MONTHS}\b'
    rf'|'
    rf'\bjul(?:y)?\.?\s*\d{{1,2}}{_ORD}\s*[-–—]\s*(?:\bjul(?:y)?\.?\s*)?\d{{1,2}}{_ORD}\b'
    rf')',
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
    if m:
        return m.group(0).strip()
    # Fall back to just the month name if no specific date found
    m2 = _MOVE_IN_MONTH_RE.search(text)
    return m2.group(0).strip() if m2 else ""


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
    if _SHORT_TERM_SUBLET_RANGE_RE.search(post.text) and not _TAKEOVER_RE.search(post.text):
        return False

    move_in_hits = _MOVE_IN_MONTH_RE.findall(post.text)
    bathroom_hits = _any_match(post.text, BATHROOM_KEYWORDS)
    location_hits = _any_match(post.text, LOCATION_KEYWORDS)

    post.matched_terms = move_in_hits + bathroom_hits + location_hits

    if not (move_in_hits and bathroom_hits and location_hits):
        return False

    post.move_in_date = _extract_move_in_date(post.text)
    post.neighborhood = _extract_neighborhood(location_hits)
    post.beds_baths = _extract_beds_baths(post.text)

    return True
