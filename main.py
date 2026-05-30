#!/usr/bin/env python3
"""
fb-sublease-finder — scrape Facebook sublease groups and surface posts within the past 24 hours that match your criteria
"""

import asyncio
import re
import sys
from collections import defaultdict
from urllib.parse import urlparse

from rich.console import Console
from rich.markup import escape
from rich.text import Text

import questionary

from config import BOROUGH_NEIGHBORHOODS
from scraper import fetch_posts
from filter import (
    Post, evaluate,
    configure_move_in_months, MONTH_NAMES,
    configure_bedroom_filter, BED_CHOICES,
    configure_bathroom_filter,
    configure_borough_filter, BOROUGH_CHOICES,
)


console = Console()

_MONTH_NUM: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _move_in_sort_key(post: Post) -> tuple[int, int]:
    """Return (month, day) for sorting; unknowns sort last."""
    d = (post.move_in_date or "").lower()
    m = re.match(r'(\d{1,2})/(\d{1,2})', d)
    if m:
        return int(m.group(1)), int(m.group(2))
    for prefix, num in _MONTH_NUM.items():
        if d.startswith(prefix):
            day = re.search(r'\d+', d[len(prefix):])
            return num, (int(day.group()) if day and int(day.group()) <= 31 else 0)
    return 99, 0


async def main(group_urls: list[str]) -> None:
    console.print(f"\n[bold][green]scanning {len(group_urls)} group(s)... this might take a moment, hang tight![/green][/bold]\n")
    posts = await fetch_posts(group_urls)
    matches = [p for p in posts if evaluate(p)]

    console.print(f"\n[bold]scanned {len(posts)} posts — [green]{len(matches)} match(es)[/green] found.[/bold]\n")

    if not matches:
        console.print("[yellow]no posts matched your criteria :([/yellow]")
        console.print("tip: check that your group URLs are correct and you're logged in.")
        return

    by_group: dict[str, list[Post]] = defaultdict(list)
    for post in matches:
        by_group[post.source_group].append(post)

    for i, (group_url, group_posts) in enumerate(by_group.items(), 1):
        console.print(f"[bold][purple]Group {i}: {escape(group_url)}[/purple][/bold]\n")

        for post in sorted(group_posts, key=_move_in_sort_key):
            console.print(
                f"  [bold]Move-in:[/bold] [green]{escape(post.move_in_date or '—')}[/green]"
                f"  [bold]·[/bold]  [bold]Neighborhood:[/bold] {escape(post.neighborhood or '—')}"
                f"  [bold]·[/bold]  [bold]Beds/Baths:[/bold] {escape(post.beds_baths or '—')}"
            )
            link = Text("  Link: ", style="bold")
            link.append(post.url, style=f"blue underline link {post.url}")
            console.print(link)
            console.print()
        console.print()


def _prompt() -> list[str]:
    """Run all questionary prompts and configure filters. Returns group URLs to search."""
    _INST = "(use arrow keys to move, space to select, and enter to submit)"

    selected_months = questionary.checkbox(
        "what’s your preferred move-in month(s)?",
        choices=MONTH_NAMES,
        instruction=_INST,
    ).unsafe_ask()

    if not selected_months:
        console.print("[yellow]no months selected, exiting.[/yellow]")
        sys.exit(0)

    configure_move_in_months(selected_months)

    selected_beds = questionary.checkbox(
        "number of bedrooms?",
        choices=BED_CHOICES,
        instruction=_INST,
    ).unsafe_ask()
    configure_bedroom_filter(selected_beds or [])

    require_bathroom = questionary.confirm(
        "private bathroom?",
        default=False,
    ).unsafe_ask()
    configure_bathroom_filter(bool(require_bathroom))

    selected_boroughs = questionary.checkbox(
        "which borough(s)?",
        choices=BOROUGH_CHOICES,
        instruction=_INST,
    ).unsafe_ask()

    selected_neighborhoods: list[str] = []
    if questionary.confirm("do you have specific neighborhood(s) in mind?", default=False).unsafe_ask():
        active_boroughs = selected_boroughs or BOROUGH_CHOICES
        neighborhood_choices: list = []
        for borough in active_boroughs:
            names = list(BOROUGH_NEIGHBORHOODS.get(borough, {}).keys())
            if names:
                neighborhood_choices.append(questionary.Separator(f"\n── {borough} ──"))
                neighborhood_choices.extend(names)
        selected_neighborhoods = questionary.checkbox(
            "select neighborhoods:",
            choices=neighborhood_choices,
            instruction=_INST,
        ).unsafe_ask() or []

    configure_borough_filter(selected_boroughs or [], selected_neighborhoods)

    console.print("[bold]paste the fb group URL that you want me to search (e.g. https://www.facebook.com/groups/1207463126375923)[/bold]")
    group_urls: list[str] = []
    while True:
        url = questionary.text(
            f"  url {len(group_urls) + 1}:" if group_urls else "  url 1:",
            instruction="(press enter with no input when done)",
        ).unsafe_ask()
        url = (url or "").strip()
        if not url:
            if not group_urls:
                console.print("[yellow]no urls entered, exiting.[/yellow]")
                sys.exit(0)
            break
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc not in ("www.facebook.com", "facebook.com"):
            console.print("[red]please enter a valid facebook.com URL.[/red]")
            continue
        group_urls.append(url)

    return group_urls


if __name__ == "__main__":
    console.print("[bold]hiii i’m here to help you find your next nyc apartment! i just have a few questions before i get started :D[/bold]\n")

    try:
        group_urls = _prompt()
        asyncio.run(main(group_urls))
    except KeyboardInterrupt:
        console.print("\n[red]program aborted bye![/red]")
        sys.exit(0)
