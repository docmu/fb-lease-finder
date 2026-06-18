from __future__ import annotations

import re
from dataclasses import dataclass, field
from config import PRIVATE_BATHROOM_KEYWORDS, BOROUGH_KEYWORDS, BOROUGH_NEIGHBORHOODS, EXCLUDE_KEYWORDS


_SEP = r'(?:[-–—]|\bto\b|\bthrough\b|\buntil\b)'    # date range separators: "–", "to", "through", "until"
_ORD = r'(?:st|nd|rd|th)?'                          # ordinal suffix: "1st", "2nd", "3rd", "4th"
_NUM = r'(?:\d+|one|two|three|four|five)'           # digit or written-out number


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
    r'(?:lease\s+)?take[-\s]?over(?:\s+(?:the\s+)?lease)?'  
    r'|re[-\s]?sign'                                          
    r'|lease\s+renew(?:al|ing)?'                             
    r'|renew(?:al|ing)?\s+(?:the\s+|my\s+)?lease'           
    r')\b',
    re.IGNORECASE,
)

# Captures the leading number/word from bedroom/bathroom counts
# e.g. "2bed", "two bedrooms", "1 br", "3 bdrm"
# (?<!\d) prevents matching mid-number (e.g. "3" in "123 bed").                                        
# (?:\.\d+)? consumes any decimal suffix so "1" in "1.5 bath" matches cleanly and the integer part is captured — "1.5 bath" → 1, "2.5 bath" → 2.                           
_BEDS_RE = re.compile(rf'(?<!\d)({_NUM})(?:\.\d+)?\s*(?:bed(?:room)?s?|bdrm|br|bd)(?![a-z])', re.IGNORECASE)  
_BATHS_RE = re.compile(rf'(?<!\d)({_NUM})(?:\.\d+)?\s*(?:bath(?:room)?s?|ba|bth)(?![a-z])', re.IGNORECASE)

BED_CHOICES: list[str] = ["Studio", "1 bed", "2 bed", "3 bed", "4 bed", "5 bed"]
BOROUGH_CHOICES: list[str] = list(BOROUGH_KEYWORDS.keys())

_NEIGHBORHOOD_KEYWORD_TO_NAME: dict[str, str] = {
    kw: name
    for nbhds in BOROUGH_NEIGHBORHOODS.values()
    for name, kws in nbhds.items()
    for kw in kws
}
_BOROUGH_KEYWORD_TO_NAME: dict[str, str] = {
    kw: borough
    for borough, kws in BOROUGH_KEYWORDS.items()
    for kw in kws
    if kw not in _NEIGHBORHOOD_KEYWORD_TO_NAME
}

# Active location keywords — replaced by configure_borough_filter()
_ACTIVE_LOCATION_KEYWORDS: list[str] = [kw for kws in BOROUGH_KEYWORDS.values() for kw in kws]

_WORD_TO_NUM: dict[str, str] = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
}


# Token separator inside multi-word keywords/phrases: ASCII hyphen plus en/em
# dashes and any whitespace, so "short-term", "short–term" (en), "short—term"
# (em) and line-wrapped "short\nterm" all match the same way.
_DASHES = r"\-\u2013\u2014"
_SEPARATOR = rf"[\s{_DASHES}]+"
# Match a straight or curly apostrophe interchangeably ("can't" ↔ "can’t").
_APOS = "['\u2019]"


def _tolerant_body(kw: str) -> str:
    """Escape `kw` into a regex body whose internal separators (spaces, hyphens,
    en/em dashes, line wraps) and apostrophes match common typographic variants.

    Returns "" when `kw` has no word content (blank / separator-only)."""
    tokens = [re.escape(t) for t in re.split(_SEPARATOR, kw.strip()) if t]
    return _SEPARATOR.join(tokens).replace("'", _APOS)


def _kw_regex(kw: str) -> str:
    """Punctuation-safe, typography-tolerant word-boundary match for a keyword.

    Keeps `(?<!\\w)…(?!\\w)` boundaries (keywords always start/end alnum) while
    tolerating dash/apostrophe/whitespace variants in multi-word neighborhoods
    ("bed-stuy" ↔ "bed–stuy", "hell's kitchen" ↔ "hell’s kitchen")."""
    body = _tolerant_body(kw)
    if not body:
        return r"(?!)"  # never matches; defensive against a blank keyword
    return rf"(?<!\w){body}(?!\w)"


def _exclude_pattern(kw: str) -> str:
    """Build a tolerant pattern for an exclude phrase.

    Internal whitespace/hyphens (incl. en/em dashes) match interchangeably and
    across line wraps (`short term` ↔ `short-term` ↔ `short–term` ↔
    `short\\nterm`). Straight and curly apostrophes are treated as equivalent
    (`can't` ↔ `can’t`). Word boundaries are only applied at edges that are
    actually word characters, so punctuation-leading tokens like `/day` still
    match when glued to a number ("$50/day").
    """
    kw = kw.strip()
    body = _tolerant_body(kw)
    if not body:
        raise ValueError("EXCLUDE_KEYWORDS contains a blank entry")
    lead = r"(?<!\w)" if kw[:1].isalnum() else ""
    trail = r"(?!\w)" if kw[-1:].isalnum() else ""
    return lead + body + trail


_EXCLUDE_RE = re.compile(
    "|".join(_exclude_pattern(kw) for kw in EXCLUDE_KEYWORDS),
    re.IGNORECASE,
)

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

    if not months:
        months = MONTH_NAMES
    
    for month in months:
        pat, num = _MONTH_DATA[month]
        broad_parts += [rf'\b{pat}\.?\b', rf'{num}/\d{{1,2}}']
        date_parts  += [rf'{num}/\d{{1,2}}', rf'{pat}\.?\s*\d{{1,2}}{_ORD}']

    _MOVE_IN_MONTH_RE = re.compile('|'.join(broad_parts), re.IGNORECASE)
    _DATE_EXTRACT_RE  = re.compile('|'.join(date_parts),  re.IGNORECASE)

    range_alts: list[str] = []
    for month in months:
        pat, num = _MONTH_DATA[month]
        other     = r'(?:' + '|'.join(p for m, (p, _) in _MONTH_DATA.items() if m != month) + r')'
        other_num = r'(?:' + '|'.join(n for m, (_, n) in _MONTH_DATA.items() if m != month) + r')'
        range_alts += [
            # cross-month text range ending in target: "June 1 – August 1", "June to August"
            rf'\b{other}.{{1,50}}?{_SEP}\s*\b{pat}\b',
            # cross-month text range starting from target: "August – September"
            rf'\b{pat}\b.{{0,20}}?{_SEP}\s*\b{other}\b',
            # within-month text range: "August 1st – August 31st", "August 1–31"
            rf'\b{pat}\.?\s*\d{{1,2}}{_ORD}\s*[-–—]\s*(?:\b{pat}\.?\s*)?\d{{1,2}}{_ORD}\b',
            # numeric cross-month range ending in target: "6/10-8/1", "6/10/2026-8/1/2026"
            rf'\b{other_num}/\d{{1,2}}(?:/\d{{2,4}})?\s*[-–—]\s*{num}/\d{{1,2}}(?:/\d{{2,4}})?\b',
            # numeric cross-month range starting from target: "8/1-9/1", "8/1/26-9/1/26"
            rf'\b{num}/\d{{1,2}}(?:/\d{{2,4}})?\s*[-–—]\s*{other_num}/\d{{1,2}}(?:/\d{{2,4}})?\b',
        ]

    _SHORT_TERM_SUBLET_RANGE_RE = re.compile(
        r'(?:' + '|'.join(range_alts) + r')',
        re.IGNORECASE,
    )


def configure_borough_filter(
    selected_boroughs: list[str],
    selected_neighborhoods: list[str] | None = None,
) -> None:
    """Restrict location matching to selected boroughs, or specific neighborhoods within them.

    Extraction (`_extract_neighborhood`) classifies hits as neighborhood vs borough on the fly via the static keyword→name maps.
    """
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
    if not selected:  # empty → no filter, allow everything
        _ALLOW_STUDIO = True
        _ALLOWED_BED_COUNTS = None
        return
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
    return [kw for kw in keywords if re.search(_kw_regex(kw), text)]


def _extract_move_in_date(text: str) -> str:
    m = _DATE_EXTRACT_RE.search(text)
    if m:
        return m.group(0).strip()
    # Fall back to just the month name if no specific date found
    m2 = _MOVE_IN_MONTH_RE.search(text)
    return m2.group(0).strip() if m2 else ""


def _extract_neighborhood(text: str, location_hits: list[str]) -> str:
    if not location_hits:
        return ""

    # Pick the keyword that appears earliest — listing titles typically name the primary neighborhood first
    def first_pos(kw: str) -> int:
        m = re.search(_kw_regex(kw), text)
        return m.start() if m else len(text)

    # Prefer a specific neighborhood over a borough-level mention
    nbhd_hits = [kw for kw in location_hits if kw in _NEIGHBORHOOD_KEYWORD_TO_NAME]
    if nbhd_hits:
        return _NEIGHBORHOOD_KEYWORD_TO_NAME[min(nbhd_hits, key=first_pos)]

    borough_hits = [kw for kw in location_hits if kw in _BOROUGH_KEYWORD_TO_NAME]
    if borough_hits:
        return _BOROUGH_KEYWORD_TO_NAME[min(borough_hits, key=first_pos)]

    return min(location_hits, key=first_pos).strip().title()


def _bed_count_value(m: re.Match) -> int:
    """Numeric bedroom count for a bed match (word numbers → int; else 0)."""
    raw = _WORD_TO_NUM.get(m.group(1), m.group(1))
    return int(raw) if raw.isdigit() else 0


def _closest_bed_bath(text: str) -> tuple[re.Match | None, re.Match | None]:
    """Pick the bed/bath match pair closest together in the text.

    Apartment specs ("3bd/2ba", "3 bed 2 bath") usually place bed and bath
    counts adjacent, while availability lines ("One Bedroom in a 3bd/2ba…")
    leave a large gap between the room count and any bath figure. Minimising
    the gap selects the spec over the availability mention.

    With no bath to anchor on, fall back to the largest bed count so the unit
    spec ("3 bedroom apartment") wins over an availability mention ("1 bedroom
    available in a 3 bedroom apartment").
    """
    beds  = list(_BEDS_RE.finditer(text))
    baths = list(_BATHS_RE.finditer(text))
    if not beds and not baths:
        return None, None
    if not baths:
        return max(beds, key=_bed_count_value), None
    if not beds:
        return None, baths[0]

    best_bed, best_bath, best_dist = beds[0], baths[0], float("inf")
    for bed_m in beds:
        for bath_m in baths:
            dist = abs(bed_m.start() - bath_m.start())
            if dist < best_dist:
                best_dist = dist
                best_bed, best_bath = bed_m, bath_m
    return best_bed, best_bath


def _extract_beds_baths(text: str) -> str:
    beds_m, baths_m = _closest_bed_bath(text)
    parts = []
    if beds_m:
        beds = _WORD_TO_NUM.get(beds_m.group(1), beds_m.group(1))
        parts.append(f"{beds} bed")
    if baths_m:
        baths = _WORD_TO_NUM.get(baths_m.group(1), baths_m.group(1))
        parts.append(f"{baths} bath")
    return " / ".join(parts)


def evaluate(post: Post) -> bool:
    """Return True if post matches all criteria and contains no excluded terms."""
    lower = post.text.lower()

    if _EXCLUDE_RE.search(lower):
        return False

    if not _ALLOW_STUDIO and "studio" in lower:
        return False

    if _ALLOWED_BED_COUNTS is not None:
        bed_m, _ = _closest_bed_bath(lower)
        if bed_m:
            count = _WORD_TO_NUM.get(bed_m.group(1), bed_m.group(1))
            if count not in _ALLOWED_BED_COUNTS:
                return False

    # TODO: maybe there is some value for short term sublets in the future
    # Drop short-term sublets unless listing mentions lease takeover/re-sign
    if _SHORT_TERM_SUBLET_RANGE_RE.search(post.text) and not _TAKEOVER_RE.search(post.text):
        return False

    move_in_hits = _MOVE_IN_MONTH_RE.findall(post.text)
    location_hits = _any_match(lower, _ACTIVE_LOCATION_KEYWORDS)
    bathroom_hits = _any_match(lower, PRIVATE_BATHROOM_KEYWORDS) if _REQUIRE_PRIVATE_BATHROOM else []

    if not move_in_hits or not location_hits:
        return False

    if _REQUIRE_PRIVATE_BATHROOM and not bathroom_hits:
        # Fallback: infer private bathroom from the apartment spec (baths >= beds)
        beds_m, baths_m = _closest_bed_bath(lower)
        if beds_m and baths_m:
            bed_n = _WORD_TO_NUM.get(beds_m.group(1), beds_m.group(1))
            bath_n = _WORD_TO_NUM.get(baths_m.group(1), baths_m.group(1))
            if not bed_n.isdigit() or not bath_n.isdigit() or int(bath_n) < int(bed_n):
                return False
        else:
            return False

    post.matched_terms = move_in_hits + bathroom_hits + location_hits

    post.move_in_date = _extract_move_in_date(post.text)
    post.neighborhood = _extract_neighborhood(lower, location_hits)
    post.beds_baths = _extract_beds_baths(post.text)

    return True
