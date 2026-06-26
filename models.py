"""Shared domain models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Post:
    text: str
    url: str
    timestamp: str
    source_group: str = ""
    posted_at: int = 0  # Unix timestamp; 0 means unknown (absolute/old date)
    matched_terms: list[str] = field(default_factory=list)
    # Structured display fields populated by filter.evaluate()
    move_in_date: str = ""
    neighborhood: str = ""
    beds_baths: str = ""
