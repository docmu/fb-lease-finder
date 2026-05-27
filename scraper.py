import asyncio
import sys
import time as _time
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page

from config import SESSION_PATH, MAX_POSTS_PER_GROUP
from filter import Post


SESSION_DIR = Path(SESSION_PATH)
_SECONDS_24H: int = 86_400


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
        print("Already logged in.")
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
    cutoff = int(_time.time()) - _SECONDS_24H

    sorted_url = _with_chronological_sort(group_url)
    await page.goto(sorted_url, wait_until="domcontentloaded")

    for _ in range(MAX_POSTS_PER_GROUP // 5 + 5):
        await page.wait_for_timeout(2_000)

        articles = await page.query_selector_all('div[role="article"]')
        hit_old_post = False

        for article in articles:
            if len(posts) >= MAX_POSTS_PER_GROUP:
                break

            try:
                # Extract post text
                text_el = await article.query_selector('[data-ad-comet-preview="message"]')
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

                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Timestamp — prefer data-utime (Unix seconds) for reliable age filtering
                time_el = await article.query_selector("abbr[data-utime]")
                posted_at = 0
                timestamp = ""
                if time_el:
                    utime = await time_el.get_attribute("data-utime")
                    if utime and utime.isdigit():
                        posted_at = int(utime)
                    timestamp = await time_el.get_attribute("title") or await time_el.inner_text()

                # Skip posts older than 24 hours; flag that we've passed the window so
                # we can stop scrolling (feed is newest-first).
                if posted_at and posted_at < cutoff:
                    hit_old_post = True
                    continue

                posts.append(Post(
                    text=text,
                    url=url or group_url,
                    timestamp=timestamp,
                    source_group=group_url,
                    posted_at=posted_at,
                ))
            except Exception:
                continue

        if len(posts) >= MAX_POSTS_PER_GROUP or hit_old_post:
            break

        await page.evaluate("window.scrollBy(0, 2000)")

    return posts


async def fetch_posts(group_urls: list[str]) -> list[Post]:
    """Launch browser with persistent session and scrape all groups."""
    SESSION_DIR.mkdir(exist_ok=True)

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
            print(f"Scraping: {_with_chronological_sort(url)}")
            try:
                group_posts = await _scrape_group(page, url)
                print(f"  → {len(group_posts)} posts within the past 24 h")
                all_posts.extend(group_posts)
            except Exception as e:
                print(f"  ! Error scraping {url}: {e}", file=sys.stderr)

        await context.close()

    return all_posts
