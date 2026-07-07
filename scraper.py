import asyncio
import re
import sys
import time as _time
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page

from config import SESSION_PATH, MAX_POSTS_PER_GROUP, SECONDS_24H
from models import Post


SESSION_DIR = Path(SESSION_PATH)


def _parse_relative_time(label: str, now: int) -> int:
    """Parse a Facebook timestamp label to Unix seconds.

    Facebook uses short relative labels for roughly the first week ("48m",
    "5h", "1d", "6d") and switches to absolute dates ("June 1 at 3:45 PM") once
    a post is 7 days or older.
    Returns 0 for absolute dates or unrecognised formats — treated as past cutoff.
    """
    label = label.strip()
    if not label:
        return 0

    low = label.lower()
    if low in ("just now", "now"):
        return now

    m = re.match(r'^(\d+)\s*s(ec(onds?)?)?$', low)
    if m:
        return now - int(m.group(1))
    m = re.match(r'^(\d+)\s*m(in(ute)?s?)?$', low)
    if m:
        return now - int(m.group(1)) * 60
    m = re.match(r'^(\d+)\s*h(rs?|ours?)?$', low)
    if m:
        return now - int(m.group(1)) * 3600
    m = re.match(r'^(\d+)\s*d(ays?)?$', low)
    if m:
        return now - int(m.group(1)) * 86_400
    return 0  # absolute date or unrecognised → treat as older than cutoff


def _with_chronological_sort(url: str) -> str:
    """Return the URL with chronological sorting appended, idempotently."""
    if "sorting_setting=CHRONOLOGICAL" in url:
        return url
    return url.rstrip("/") + "/?sorting_setting=CHRONOLOGICAL"


async def _ensure_logged_in(context: BrowserContext) -> None:
    """Open Facebook and block until the user is on a logged-in page."""
    page = await context.new_page()
    await page.goto("https://www.facebook.com")
    await page.wait_for_load_state("domcontentloaded")

    try:
        await page.wait_for_selector('[aria-label="Home"]', timeout=5_000)
        print("already logged in.")
        await page.close()
        return
    except Exception:
        pass

    print("\nNot logged in. A browser window will open — please log in manually.")
    print("The script will continue automatically once you reach the Facebook feed.\n")
    await page.wait_for_selector('[aria-label="Home"]', timeout=300_000)
    print("Login detected. Saving session...")
    await page.close()


async def _scrape_group(page: Page, group_url: str) -> list[Post]:
    """Navigate to a group (sorted by newest) and collect posts from the past 24 hours."""
    posts: list[Post] = []
    seen_urls: set[str] = set()
    cutoff = int(_time.time()) - SECONDS_24H

    # A single old post (e.g. a pinned announcement at the top of a
    # chronological feed) shouldn't abort the scrape. Only stop once we've seen
    # a run of consecutive confirmed-old posts, which reliably means we've
    # scrolled past the 24h window.
    consecutive_old = 0
    OLD_RUN_LIMIT = 5

    sorted_url = _with_chronological_sort(group_url)
    await page.goto(sorted_url, wait_until="domcontentloaded")

    for _ in range(MAX_POSTS_PER_GROUP // 5 + 5):
        await page.wait_for_timeout(2_000)

        articles = await page.query_selector_all('div[role="article"]')

        for article in articles:
            if len(posts) >= MAX_POSTS_PER_GROUP:
                break

            try:
                # Extract post text
                text_el = await article.query_selector('[data-ad-comet-preview="message"]')
                # expand "See more" first if the post is truncated
                see_more = await article.query_selector('[role="button"]:has-text("See more")')
                if see_more:
                    try:
                        await see_more.click()
                        await page.wait_for_timeout(300)
                    except Exception:
                        pass
                if not text_el:
                    text = await article.inner_text()
                else:
                    text = await text_el.inner_text()

                if not text.strip():
                    continue

                # Permalink
                link_el = await article.query_selector('a[href*="/posts/"], a[href*="?story_fbid="], a[href*="/permalink/"]')
                url = await link_el.get_attribute("href") if link_el else group_url
                if url and url.startswith("/"):
                    url = "https://www.facebook.com" + url
                # Strip tracking params
                if url:
                    url = url.split("?")[0]

                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Timestamp — the post's permalink also carries the time label.
                # Groups render permalinks in different formats (/posts/,
                # /permalink/, ?story_fbid=), so accept all three, and read the
                # relative label from either the link text ("5h") or aria-label.
                time_el = await article.query_selector(
                    'a[href*="/posts/"], a[href*="/permalink/"], a[href*="?story_fbid="]'
                )
                posted_at = 0 # default: absolute date format (e.g. "June 1", greater than 24h)
                timestamp = ""
                if time_el:
                    text_label = (await time_el.inner_text() or "").strip()
                    aria_label = (await time_el.get_attribute("aria-label") or "").strip()
                    for candidate in (text_label, aria_label):
                        posted_at = _parse_relative_time(candidate, now)
                        if posted_at:
                            timestamp = candidate
                            break

                if not posted_at:
                    if time_el:           # element found but absolute date → confirmed old
                        consecutive_old += 1
                    continue              # no element (pinned/ad) → skip silently
                if posted_at <= cutoff:   # "past 24 h" = strictly younger than 24h
                    consecutive_old += 1
                    continue
                consecutive_old = 0       # a fresh post resets the run

                posts.append(Post(
                    text=text,
                    url=url or group_url,
                    timestamp=timestamp,
                    source_group=group_url,
                    posted_at=posted_at,
                ))
            except Exception:
                continue

        if len(posts) >= MAX_POSTS_PER_GROUP or consecutive_old >= OLD_RUN_LIMIT:
            break

        await page.evaluate("window.scrollBy(0, 2000)")

    return posts


async def fetch_posts(group_urls: list[str]) -> list[Post]:
    """Launch browser with persistent session and scrape all groups."""
    SESSION_DIR.mkdir(mode=0o700, exist_ok=True)

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
        )

        await _ensure_logged_in(context)

        all_posts: list[Post] = []
        page = await context.new_page()

        for url in group_urls:
            print(f"scraping: {url}")
            try:
                group_posts = await _scrape_group(page, url)
                print(f"  → {len(group_posts)} posts within the past 24 h")
                all_posts.extend(group_posts)
            except Exception as e:
                print(f"  ! Error scraping {url}: {e}", file=sys.stderr)

        await context.close()

    return all_posts
