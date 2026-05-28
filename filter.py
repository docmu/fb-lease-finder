from __future__ import annotations

import re
from dataclasses import dataclass, field
from config import PRIVATE_BATHROOM_KEYWORDS, BOROUGH_KEYWORDS, BOROUGH_NEIGHBORHOODS, EXCLUDE_KEYWORDS


# Shared building blocks used inside dynamically compiled regexes below
_SEP = r'(?:[-–—]|\bto\b|\bthrough\b|\buntil\b)'  # date range separators: "–", "to", "through", "until"
_ORD = r'(?:st|nd|rd|th)?'                          # optional ordinal suffix: "1st", "2nd", "3rd", "4th"
_NUM = r'(?:\d+|one|two|three)'                     # digit or written-out number up to three

# (abbreviated_pattern, numeric_string) for each month
_MONTH_DATA: dict[str, tuple[str, str]] = {
    "January":   ("jan(?:uary)?",   "1"),
    "February":  ("feb(?:ruary)?",  "2"),
    "March":     ("mar(?:ch)?",     "3"),
    "April":     ("apr(?:il)?",     "4"),
    "May":       ("may",            "5"),
    "June":      ("jun(?:e)?",      "6"),
    "July":      ("jul(?:y)?",      "7"),
    "August":    ("aug(?:ust)?",    "8"),
    "September": ("sep(?:tember)?", "9"),
    "October":   ("oct(?:ober)?",   "10"),
    "November":  ("nov(?:ember)?",  "11"),
    "December":  ("dec(?:ember)?",  "12"),
}

MONTH_NAMES: list[str] = list(_MONTH_DATA.keys())

# Placeholders replaced by configure_move_in_months() before first use
_MOVE_IN_MONTH_RE: re.Pattern = re.compile(r'(?!)')
_DATE_EXTRACT_RE: re.Pattern = re.compile(r'(?!)')
_SHORT_TERM_SUBLET_RANGE_RE: re.Pattern = re.compile(r'(?!)')

# Matches lease continuation mentions — these override the short-term sublet filter
# e.g. "lease takeover", "take over the lease", "re-sign", "lease renewal", "renewing my lease"
_TAKEOVER_RE = re.compile(
    r'\b(?:'
    r'(?:lease\s+)?take[-\s]?over(?:\s+(?:the\s+)?lease)?'  # take over / lease takeover / take over the lease
    r'|re[-\s]?sign'                                          # re-sign / resign
    r'|lease\s+renew(?:al|ing)?'                             # lease renewal / lease renewing
    r'|renew(?:al|ing)?\s+(?:the\s+|my\s+)?lease'           # renew lease / renewing my lease / renewal of the lease
    r')\b',
    re.IGNORECASE,
)

# Captures the leading number/word from bedroom/bathroom counts
# e.g. "2bed", "two bedrooms", "1 br", "3 bdrm"
_BEDS_RE = re.compile(rf'({_NUM})\s*(?:bed(?:room)?s?|bdrm|br|bd)\b', re.IGNORECASE)
_BATHS_RE = re.compile(rf'({_NUM})\s*(?:bath(?:room)?s?|ba|bth|br)\b', re.IGNORECASE)

BED_CHOICES: list[str] = ["Studio", "1 bed", "2 bed", "3 bed", "4 bed", "5 bed"]
BOROUGH_CHOICES: list[str] = list(BOROUGH_KEYWORDS.keys())

# Active location keywords — replaced by configure_borough_filter()
_ACTIVE_LOCATION_KEYWORDS: list[str] = [kw for kws in BOROUGH_KEYWORDS.values() for kw in kws]

_WORD_TO_NUM: dict[str, str] = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
}

# Set by configure_bedroom_filter(); None means no filter applied
_ALLOW_STUDIO: bool = True
_ALLOWED_BED_COUNTS: frozenset[str] | None = None

_REQUIRE_PRIVATE_BATHROOM: bool = False


def configure_bathroom_filter(require: bool) -> None:
    global _REQUIRE_PRIVATE_BATHROOM
    _REQUIRE_PRIVATE_BATHROOM = require


def configure_move_in_months(months: list[str]) -> None:
    """Build all month-dependent regexes from the user's selection."""
    global _MOVE_IN_MONTH_RE, _DATE_EXTRACT_RE, _SHORT_TERM_SUBLET_RANGE_RE

    broad_parts: list[str] = []
    date_parts: list[str] = []

    for month in months:
        pat, num = _MONTH_DATA[month]
        broad_parts += [rf'\b{pat}\.?\b', rf'{num}/\d{{1,2}}']
        date_parts  += [rf'{num}/\d{{1,2}}', rf'{pat}\.?\s*\d{{1,2}}{_ORD}']

    _MOVE_IN_MONTH_RE = re.compile('|'.join(broad_parts), re.IGNORECASE)
    _DATE_EXTRACT_RE  = re.compile('|'.join(date_parts),  re.IGNORECASE)

    range_alts: list[str] = []
    for month in months:
        pat, _ = _MONTH_DATA[month]
        other = r'(?:' + '|'.join(p for m, (p, _) in _MONTH_DATA.items() if m != month) + r')'
        range_alts += [
            rf'\b{other}.{{1,50}}?{_SEP}\s*\b{pat}\b',
            rf'\b{pat}\b.{{0,20}}?{_SEP}\s*\b{other}\b',
            rf'\b{pat}\.?\s*\d{{1,2}}{_ORD}\s*[-–—]\s*(?:\b{pat}\.?\s*)?\d{{1,2}}{_ORD}\b',
        ]

    _SHORT_TERM_SUBLET_RANGE_RE = re.compile(
        r'(?:' + '|'.join(range_alts) + r')',
        re.IGNORECASE,
    )


def configure_borough_filter(
    selected_boroughs: list[str],
    selected_neighborhoods: list[str] | None = None,
) -> None:
    """Restrict location matching to selected boroughs, or specific neighborhoods within them."""
    global _ACTIVE_LOCATION_KEYWORDS
    if selected_neighborhoods:
        active_boroughs = selected_boroughs or list(BOROUGH_KEYWORDS.keys())
        kws: list[str] = []
        for borough in active_boroughs:
            nbhd_map = BOROUGH_NEIGHBORHOODS.get(borough, {})
            for nbhd in selected_neighborhoods:
                kws.extend(nbhd_map.get(nbhd, []))
        _ACTIVE_LOCATION_KEYWORDS = kws
    elif not selected_boroughs:
        _ACTIVE_LOCATION_KEYWORDS = [kw for kws in BOROUGH_KEYWORDS.values() for kw in kws]
    else:
        _ACTIVE_LOCATION_KEYWORDS = [kw for b in selected_boroughs for kw in BOROUGH_KEYWORDS[b]]


def configure_bedroom_filter(selected: list[str]) -> None:
    """Set bedroom inclusion rules from the user's selection."""
    global _ALLOW_STUDIO, _ALLOWED_BED_COUNTS
    _ALLOW_STUDIO = "Studio" in selected
    counts = {s.split()[0] for s in selected if s != "Studio"}
    _ALLOWED_BED_COUNTS = frozenset(counts) if counts else None


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
    return [kw for kw in keywords if re.search(r'\b' + re.escape(kw.strip()) + r'\b', lower)]


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

    if not _ALLOW_STUDIO and "studio" in lower:
        return False

    if _ALLOWED_BED_COUNTS is not None:
        bed_m = _BEDS_RE.search(post.text)
        if bed_m:
            count = _WORD_TO_NUM.get(bed_m.group(1).lower(), bed_m.group(1))
            if count not in _ALLOWED_BED_COUNTS:
                return False

    # Drop short-term sublets (e.g. June - August) unless it's a lease takeover/re-sign
    if _SHORT_TERM_SUBLET_RANGE_RE.search(post.text) and not _TAKEOVER_RE.search(post.text):
        return False

    move_in_hits = _MOVE_IN_MONTH_RE.findall(post.text)
    bathroom_hits = _any_match(post.text, PRIVATE_BATHROOM_KEYWORDS) if _REQUIRE_PRIVATE_BATHROOM else []
    location_hits = _any_match(post.text, _ACTIVE_LOCATION_KEYWORDS)

    post.matched_terms = move_in_hits + bathroom_hits + location_hits

    if not move_in_hits or not location_hits:
        return False
    if _REQUIRE_PRIVATE_BATHROOM and not bathroom_hits:
        return False

    post.move_in_date = _extract_move_in_date(post.text)
    post.neighborhood = _extract_neighborhood(location_hits)
    post.beds_baths = _extract_beds_baths(post.text)

    return True
