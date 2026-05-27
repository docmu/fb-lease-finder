GROUP_URLS: list[str] = [
    # Add your Facebook group URLs here, e.g.:
    # "https://www.facebook.com/groups/123456789/?sorting_setting=CHRONOLOGICAL",
    "https://www.facebook.com/groups/3668775323228109/?sorting_setting=CHRONOLOGICAL",
    "https://www.facebook.com/groups/1207463126375923/?sorting_setting=CHRONOLOGICAL",
    "https://www.facebook.com/groups/573045118309642/?sorting_setting=CHRONOLOGICAL",
    "https://www.facebook.com/groups/2050201058584087/?sorting_setting=CHRONOLOGICAL",
    "https://www.facebook.com/groups/williamsburggreenpointhousing/?sorting_setting=CHRONOLOGICAL",
    "https://www.facebook.com/groups/217717306455238/?sorting_setting=CHRONOLOGICAL",
]

# Keyword sets — a post must match at least one term from EACH active group to qualify.
# Set a group to None to disable that filter.

MOVE_IN_KEYWORDS: list[str] = [
    "august",
    "aug",
    "8/1",
    "available august",
    "move in august",
    "starting august",
]

BATHROOM_KEYWORDS: list[str] = [
    "private bath",
    "private bathroom",
    "own bath",
    "own bathroom",
    "en suite",
    "ensuite",
    "en-suite",
    "private restroom",
]

LOCATION_KEYWORDS: list[str] = [
    "brooklyn",
    " bk ",   # spaced to avoid false matches like "bklyn"
    "bklyn",
    "bed-stuy",
    "bedstuy",
    "bed stuy",
    "williamsburg",
    "crown heights",
    "park slope",
    "prospect heights",
    "greenpoint",
    "carroll gardens",
    "cobble hill",
    "fort greene",
    "fort green",
    "clinton hill"
    "gowanus",
    "dumbo",
    "downtown brooklyn",
    "boerum hill",
]

# Posts are excluded if they contain ANY of these terms (case-insensitive).
EXCLUDE_KEYWORDS: list[str] = [
    "short term",
    "short-term",
    "summer sublet",
    "studio",
    "1 bed/1 bath",
    "1 bed/ 1 bath",
    "1 bd/1ba",
    "1bd / 1ba"
    "one bed/one bath",
    "one bed/ one bath",
]

# How many posts to scrape per group per run
MAX_POSTS_PER_GROUP: int = 50

# Browser session storage path (keeps you logged in between runs)
SESSION_PATH: str = "session"
