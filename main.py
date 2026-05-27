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

from config import GROUP_URLS
from scraper import fetch_posts
from filter import Post, evaluate


console = Console()


def _group_label(url: str) -> str:
    """Extract the group slug or ID from a Facebook group URL."""
    parts = urlparse(url).path.strip("/").split("/")
    return parts[1] if len(parts) >= 2 else url


async def main() -> None:
    if not GROUP_URLS:
        console.print("[red]No group URLs configured.[/red] Add them to [bold]config.py[/bold] → GROUP_URLS.")
        sys.exit(1)

    console.print(f"\n[bold]Scanning {len(GROUP_URLS)} group(s)…[/bold]\n")
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
    asyncio.run(main())
