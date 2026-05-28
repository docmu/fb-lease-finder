#!/usr/bin/env python3
"""
fb-sublease-finder — scrape Facebook sublease groups and surface posts
matching: August move-in + private bathroom + Brooklyn.
"""

import asyncio
import sys
from collections import defaultdict
from urllib.parse import urlparse

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

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


def _group_label(url: str) -> str:
    """Extract the group slug or ID from a Facebook group URL."""
    parts = urlparse(url).path.strip("/").split("/")
    return parts[1] if len(parts) >= 2 else url


async def main(group_urls: list[str]) -> None:
    console.print(f"\n[bold]scanning {len(group_urls)} group(s)... this might take a moment, hang tight![/bold]\n")
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

    for group_url, group_posts in by_group.items():
        count = len(group_posts)
        console.print(f"[dim]{group_url}[/dim]")

        table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold", padding=(0, 1))
        table.add_column("Move-in", style="green", min_width=14)
        table.add_column("Neighborhood", min_width=18)
        table.add_column("Beds / Baths", min_width=14)
        table.add_column("Link")

        for post in group_posts:
            link = Text("View post →", style=f"blue underline link {post.url}") 
            table.add_row(
                post.move_in_date or "—",
                post.neighborhood or "—",
                post.beds_baths or "—",
                link,
            )

        console.print(table)
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

    console.print("paste the fb group URL that you want me to search (e.g. https://www.facebook.com/groups/1207463126375923)\n")
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
        group_urls.append(url)

    return group_urls


if __name__ == "__main__":
    console.print("[green]hiii i’m here to help you find your next nyc apartment! i just have a few questions before i get started :D[/green]\n")

    try:
        group_urls = _prompt()
        asyncio.run(main(group_urls))
    except KeyboardInterrupt:
        console.print("\n[red]program aborted bye![/red]")
        sys.exit(0)
