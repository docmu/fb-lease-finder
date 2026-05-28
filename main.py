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

from config import GROUP_URLS, BOROUGH_NEIGHBORHOODS
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


async def main(selected_months: list[str]) -> None:
    console.print(f"\n[bold]Scanning {len(GROUP_URLS)} group(s) for {', '.join(selected_months)} move-ins…[/bold]\n")
    posts = await fetch_posts(GROUP_URLS)
    matches = [p for p in posts if evaluate(p)]

    console.print(f"\n[bold]Scanned {len(posts)} posts — [green]{len(matches)} match(es)[/green] found.[/bold]\n")

    if not matches:
        console.print("[yellow]No posts matched your criteria :([/yellow]")
        console.print("Tip: check that your group URLs are correct and you're logged in.")
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


if __name__ == "__main__":
    """runs synchronously before asyncio.run() starts and the results are passed into main()"""
    if not GROUP_URLS:
        console.print("[red]No group URLs configured.[/red] Add them to [bold]config.py[/bold] → GROUP_URLS.")
        sys.exit(1)

    selected = questionary.checkbox(
        "Select your preferred move-in month(s):",
        choices=MONTH_NAMES,
        instruction="(use arrow keys to move, space to select, and enter to submit)"
    ).ask()

    if not selected:
        console.print("[yellow]No months selected, exiting.[/yellow]")
        sys.exit(0)

    configure_move_in_months(selected)

    selected_beds = questionary.checkbox(
        "Number of bedrooms?",
        choices=BED_CHOICES,
        instruction="(use arrow keys to move, space to select, and enter to submit)"
    ).ask()

    configure_bedroom_filter(selected_beds or [])

    require_bathroom = questionary.confirm(
        "Private bathroom?",
        default=False,
    ).ask()
    configure_bathroom_filter(bool(require_bathroom))

    selected_boroughs = questionary.checkbox(
        "Which borough(s)?",
        choices=BOROUGH_CHOICES,
        instruction="(use arrow keys to move, space to select, and enter to submit)"
    ).ask()

    selected_neighborhoods: list[str] = []
    want_specific = questionary.confirm(
        "Do you have specific neighborhoods in mind?",
        default=False,
    ).ask()
    if want_specific:
        active_boroughs = selected_boroughs or BOROUGH_CHOICES
        neighborhood_choices = []
        for borough in active_boroughs:
            names = list(BOROUGH_NEIGHBORHOODS.get(borough, {}).keys())
            if names:
                neighborhood_choices.append(questionary.Separator(f"\n── {borough} ──\n"))
                neighborhood_choices.extend(names)
        selected_neighborhoods = questionary.checkbox(
            "Select neighborhoods:",
            choices=neighborhood_choices,
            instruction="(use arrow keys to move, space to select, and enter to submit)"
        ).ask() or []

    configure_borough_filter(selected_boroughs or [], selected_neighborhoods or [])
    asyncio.run(main(selected))
