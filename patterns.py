"""Stateless regex machinery and text extraction for post filtering.

Everything here is a pure function of its inputs (plus the static keyword data
in `config`). All mutable, user-selected filter state lives in `filter.py`.
"""

from __future__ import annotations

import re

from config import BOROUGH_KEYWORDS, BOROUGH_NEIGHBORHOODS, EXCLUDE_KEYWORDS


# --- Shared regex building blocks ---------------------------------------------

_SEP = r'(?:[-–—]|\bto\b|\bthrough\b|\buntil\b)'    # date range separators: "–", "to", "through", "until"
_ORD = r'(?:st|nd|rd|th)?'                          # ordinal suffix: "1st", "2nd", "3rd", "4th"
_NUM = r'(?:\d+|one|two|three|four|five)'           # digit or written-out number

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

WORD_TO_NUM: dict[str, str] = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
}


# --- Bed / bath / takeover patterns -------------------------------------------

# Captures the leading number/word from bedroom/bathroom counts
# e.g. "2bed", "two bedrooms", "1 br", "3 bdrm", "4-bedroom"
# (?<!\d) prevents matching mid-number (e.g. "3" in "123 bed").
# (?:\.\d+)? consumes any decimal suffix so "1" in "1.5 bath" matches cleanly and the integer part is captured — "1.5 bath" → 1, "2.5 bath" → 2.
# [\s\u2013\u2014-]* allows a space, hyphen, or en/em dash between the count and the unit.
BEDS_RE = re.compile(rf'(?<!\d)({_NUM})(?:\.\d+)?[\s\u2013\u2014-]*(?:bed(?:room)?s?|bdrm|br|bd)(?![a-z])', re.IGNORECASE)
BATHS_RE = re.compile(rf'(?<!\d)({_NUM})(?:\.\d+)?[\s\u2013\u2014-]*(?:bath(?:room)?s?|ba|bth)(?![a-z])', re.IGNORECASE)

# Matches lease continuation mentions — these override the short-term sublet filter
# e.g. "lease takeover", "take over the lease", "re-sign", "lease renewal", "renewing my lease"
TAKEOVER_RE = re.compile(
    r'\b(?:'
    r'(?:lease\s+)?take[-\s]?over(?:\s+(?:the\s+)?lease)?'
    r'|re[-\s]?sign'
    r'|lease\s+renew(?:al|ing)?'
    r'|renew(?:al|ing)?\s+(?:the\s+|my\s+)?lease'
    r')\b',
    re.IGNORECASE,
)


# --- Keyword → canonical name maps (built once from config) -------------------

NEIGHBORHOOD_KEYWORD_TO_NAME: dict[str, str] = {
    kw: name
    for nbhds in BOROUGH_NEIGHBORHOODS.values()
    for name, kws in nbhds.items()
    for kw in kws
}
BOROUGH_KEYWORD_TO_NAME: dict[str, str] = {
    kw: borough
    for borough, kws in BOROUGH_KEYWORDS.items()
    for kw in kws
    if kw not in NEIGHBORHOOD_KEYWORD_TO_NAME
}


# --- Typography-tolerant keyword matching -------------------------------------

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


def keyword_regex(kw: str) -> str:
    """Punctuation-safe, typography-tolerant word-boundary match for a keyword.

    Keeps `(?<!\\w)…(?!\\w)` boundaries (keywords always start/end alnum) while
    tolerating dash/apostrophe/whitespace variants in multi-word neighborhoods
    ("bed-stuy" ↔ "bed–stuy", "hell's kitchen" ↔ "hell’s kitchen")."""
    body = _tolerant_body(kw)
    if not body:
        return r"(?!)"  # never matches; defensive against a blank keyword
    return rf"(?<!\w){body}(?!\w)"


# Every location keyword we know about (neighborhoods + borough catch-alls).
# Used to find a post's *primary* location across all neighborhoods — even ones
# the user didn't select — so we can drop posts whose main location is elsewhere.
ALL_LOCATION_KEYWORDS: list[str] = (
    list(NEIGHBORHOOD_KEYWORD_TO_NAME) + list(BOROUGH_KEYWORD_TO_NAME)
)


def location_name(kw: str) -> str:
    """Canonical display name for a location keyword."""
    return (
        NEIGHBORHOOD_KEYWORD_TO_NAME.get(kw)
        or BOROUGH_KEYWORD_TO_NAME.get(kw)
        or kw.strip().title()
    )


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


EXCLUDE_RE = re.compile(
    "|".join(_exclude_pattern(kw) for kw in EXCLUDE_KEYWORDS),
    re.IGNORECASE,
)


# --- Move-in date pattern builder ---------------------------------------------

def build_move_in_patterns(
    months: list[str],
) -> tuple[re.Pattern, re.Pattern, re.Pattern]:
    """Compile the (broad month, specific date, short-term sublet range) regexes
    for the selected months. An empty selection means "all months".

    Returns a tuple of (move_in_month_re, date_extract_re, sublet_range_re).
    """
    if not months:
        months = MONTH_NAMES

    broad_parts: list[str] = []
    date_parts: list[str] = []
    for month in months:
        pat, num = _MONTH_DATA[month]
        broad_parts += [rf'\b{pat}\.?\b', rf'{num}/\d{{1,2}}']
        date_parts  += [rf'{num}/\d{{1,2}}', rf'{pat}\.?\s*\d{{1,2}}{_ORD}']

    move_in_re = re.compile('|'.join(broad_parts), re.IGNORECASE)
    date_re    = re.compile('|'.join(date_parts),  re.IGNORECASE)

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

    sublet_range_re = re.compile(r'(?:' + '|'.join(range_alts) + r')', re.IGNORECASE)
    return move_in_re, date_re, sublet_range_re


# --- Bed / bath extraction ----------------------------------------------------

def _bed_count_value(m: re.Match) -> int:
    """Numeric bedroom count for a bed match (word numbers → int; else 0)."""
    raw = WORD_TO_NUM.get(m.group(1), m.group(1))
    return int(raw) if raw.isdigit() else 0


def closest_bed_bath(text: str) -> tuple[re.Match | None, re.Match | None]:
    """Pick the bed/bath match pair closest together in the text.

    Apartment specs ("3bd/2ba", "3 bed 2 bath") usually place bed and bath
    counts adjacent, while availability lines ("One Bedroom in a 3bd/2ba…")
    leave a large gap between the room count and any bath figure. Minimising
    the gap selects the spec over the availability mention.

    With no bath to anchor on, fall back to the largest bed count so the unit
    spec ("3 bedroom apartment") wins over an availability mention ("1 bedroom
    available in a 3 bedroom apartment").
    """
    beds  = list(BEDS_RE.finditer(text))
    baths = list(BATHS_RE.finditer(text))
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


def extract_beds_baths(text: str) -> str:
    beds_m, baths_m = closest_bed_bath(text)
    parts = []
    if beds_m:
        beds = WORD_TO_NUM.get(beds_m.group(1), beds_m.group(1))
        parts.append(f"{beds} bed")
    if baths_m:
        baths = WORD_TO_NUM.get(baths_m.group(1), baths_m.group(1))
        parts.append(f"{baths} bath")
    return " / ".join(parts)
