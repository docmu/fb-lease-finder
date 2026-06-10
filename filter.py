from __future__ import annotations

import re
from dataclasses import dataclass, field

from config import PRIVATE_BATHROOM_KEYWORDS, BOROUGH_KEYWORDS, BOROUGH_NEIGHBORHOODS
from patterns import (
    MONTH_NAMES,
    WORD_TO_NUM,
    EXCLUDE_RE,
    TAKEOVER_RE,
    NEIGHBORHOOD_KEYWORD_TO_NAME,
    BOROUGH_KEYWORD_TO_NAME,
    keyword_regex,
    build_move_in_patterns,
    closest_bed_bath,
    extract_beds_baths,
)

# Re-exported for callers (main.py) that import choices from this module.
__all__ = [
    "Post", "evaluate", "MONTH_NAMES", "BED_CHOICES", "BOROUGH_CHOICES",
    "configure_move_in_months", "configure_bedroom_filter",
    "configure_bathroom_filter", "configure_borough_filter",
]

BED_CHOICES: list[str] = ["Studio", "1 bed", "2 bed", "3 bed", "4 bed", "5 bed"]
BOROUGH_CHOICES: list[str] = list(BOROUGH_KEYWORDS.keys())


# --- Mutable filter state (set by the configure_* functions) ------------------

# Move-in regexes — placeholders that never match until configure_move_in_months()
_MOVE_IN_MONTH_RE: re.Pattern = re.compile(r'(?!)')
_DATE_EXTRACT_RE: re.Pattern = re.compile(r'(?!)')
_SHORT_TERM_SUBLET_RANGE_RE: re.Pattern = re.compile(r'(?!)')

# Active location keywords — replaced by configure_borough_filter()
_ACTIVE_LOCATION_KEYWORDS: list[str] = [kw for kws in BOROUGH_KEYWORDS.values() for kw in kws]

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
    _MOVE_IN_MONTH_RE, _DATE_EXTRACT_RE, _SHORT_TERM_SUBLET_RANGE_RE = build_move_in_patterns(months)


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
    return [kw for kw in keywords if re.search(keyword_regex(kw), text)]


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
<<<<<<< HEAD
=======
    lower = text.lower()
    # Pick the keyword that appears earliest — listing titles name the primary
    # neighborhood first; secondary mentions ("walking distance to X") come later.
    def first_pos(kw: str) -> int:
        m = re.search(r'\b' + re.escape(kw.strip()) + r'\b', lower)
        return m.start() if m else len(lower)
    return min(location_hits, key=first_pos).strip().title()
>>>>>>> 15beaed (fix: .5 bath & posted_at bug, add more neighborhoods, rename repro)

    # Pick the keyword that appears earliest — listing titles typically name the primary neighborhood first
    def first_pos(kw: str) -> int:
        m = re.search(keyword_regex(kw), text)
        return m.start() if m else len(text)

    # Prefer a specific neighborhood over a borough-level mention
    nbhd_hits = [kw for kw in location_hits if kw in NEIGHBORHOOD_KEYWORD_TO_NAME]
    if nbhd_hits:
        return NEIGHBORHOOD_KEYWORD_TO_NAME[min(nbhd_hits, key=first_pos)]

    borough_hits = [kw for kw in location_hits if kw in BOROUGH_KEYWORD_TO_NAME]
    if borough_hits:
        return BOROUGH_KEYWORD_TO_NAME[min(borough_hits, key=first_pos)]

    return min(location_hits, key=first_pos).strip().title()


def evaluate(post: Post) -> bool:
    """Return True if post matches all criteria and contains no excluded terms."""
    lower = post.text.lower()

    if EXCLUDE_RE.search(lower):
        return False

    if not _ALLOW_STUDIO and "studio" in lower:
        return False

    if _ALLOWED_BED_COUNTS is not None:
        bed_m, _ = closest_bed_bath(lower)
        if bed_m:
            count = WORD_TO_NUM.get(bed_m.group(1), bed_m.group(1))
            if count not in _ALLOWED_BED_COUNTS:
                return False

    # TODO: maybe there is some value for short term sublets in the future
    # Drop short-term sublets unless listing mentions lease takeover/re-sign
    if _SHORT_TERM_SUBLET_RANGE_RE.search(post.text) and not TAKEOVER_RE.search(post.text):
        return False

    move_in_hits = _MOVE_IN_MONTH_RE.findall(post.text)
    location_hits = _any_match(lower, _ACTIVE_LOCATION_KEYWORDS)
    bathroom_hits = _any_match(lower, PRIVATE_BATHROOM_KEYWORDS) if _REQUIRE_PRIVATE_BATHROOM else []

    if not move_in_hits or not location_hits:
        return False

    if _REQUIRE_PRIVATE_BATHROOM and not bathroom_hits:
        # Fallback: infer private bathroom from the apartment spec (baths >= beds)
        beds_m, baths_m = closest_bed_bath(lower)
        if beds_m and baths_m:
            bed_n = WORD_TO_NUM.get(beds_m.group(1), beds_m.group(1))
            bath_n = WORD_TO_NUM.get(baths_m.group(1), baths_m.group(1))
            if not bed_n.isdigit() or not bath_n.isdigit() or int(bath_n) < int(bed_n):
                return False
        else:
            return False

    post.matched_terms = move_in_hits + bathroom_hits + location_hits

    post.move_in_date = _extract_move_in_date(post.text)
<<<<<<< HEAD
    post.neighborhood = _extract_neighborhood(lower, location_hits)
    post.beds_baths = extract_beds_baths(post.text)
=======
    post.neighborhood = _extract_neighborhood(post.text, location_hits)
    post.beds_baths = _extract_beds_baths(post.text)
>>>>>>> 15beaed (fix: .5 bath & posted_at bug, add more neighborhoods, rename repro)

    return True
