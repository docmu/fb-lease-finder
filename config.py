GROUP_URLS: list[str] = [
    # Add your Facebook group URLs here:
    "https://www.facebook.com/groups/1207463126375923",
    "https://www.facebook.com/groups/3668775323228109",
    "https://www.facebook.com/groups/573045118309642",
    "https://www.facebook.com/groups/2050201058584087",
    "https://www.facebook.com/groups/williamsburggreenpointhousing",
    "https://www.facebook.com/groups/217717306455238",
]

# Keyword sets — a post must match at least one term from EACH active group to qualify.
# Set a group to None to disable that filter.

PRIVATE_BATHROOM_KEYWORDS: list[str] = [
    "private bath",
    "private bathroom",
    "own bath",
    "own bathroom",
    "en suite",
    "ensuite",
    "en-suite",
    "private restroom",
]

BOROUGH_NEIGHBORHOODS: dict[str, dict[str, list[str]]] = {
    "Brooklyn": {
        "Bed-Stuy":          ["bed-stuy", "bedstuy", "bed stuy"],
        "Williamsburg":      ["williamsburg"],
        "Crown Heights":     ["crown heights"],
        "Park Slope":        ["park slope"],
        "Prospect Heights":  ["prospect heights"],
        "Greenpoint":        ["greenpoint"],
        "Carroll Gardens":   ["carroll gardens"],
        "Cobble Hill":       ["cobble hill"],
        "Fort Greene":       ["fort greene", "fort green"],
        "Clinton Hill":      ["clinton hill"],
        "Gowanus":           ["gowanus"],
        "DUMBO":             ["dumbo"],
        "Downtown Brooklyn": ["downtown brooklyn"],
        "Boerum Hill":       ["boerum hill"],
        "Bushwick":          ["bushwick"],
        "Flatbush":          ["flatbush"],
        "Sunset Park":       ["sunset park"],
        "Bay Ridge":         ["bay ridge", "bayridge"],
        "Red Hook":          ["red hook", "redhook"],
    },
    "Manhattan": {
        "Upper East Side":    ["upper east side", " ues "],
        "Upper West Side":    ["upper west side", " uws "],
        "Lower East Side":    ["lower east side", " les "],
        "East Village":       ["east village"],
        "West Village":       ["west village"],
        "Chelsea":            ["chelsea"],
        "Hell's Kitchen":     ["hell's kitchen", "hells kitchen"],
        "Midtown":            ["midtown"],
        "Harlem":             ["harlem"],
        "East Harlem":        ["east harlem"],
        "Washington Heights": ["washington heights"],
        "Inwood":             ["inwood"],
        "Tribeca":            ["tribeca"],
        "SoHo":               ["soho"],
        "Nolita":             ["nolita"],
        "Financial District": ["financial district", "fidi"],
        "Gramercy":           ["gramercy"],
        "Murray Hill":        ["murray hill"],
        "Kips Bay":           ["kips bay"],
        "Morningside Heights":["morningside heights"],
        "Hamilton Heights":   ["hamilton heights"],
        "Sugar Hill":         ["sugar hill"],
        "NoHo":               ["noho"],
        "Flatiron":           ["flatiron"],
        "NoMad":              ["nomad"],
    },
    "Queens": {
        "Astoria":         ["astoria"],
        "Long Island City":["long island city", " lic "],
        "Sunnyside":       ["sunnyside"],
        "Woodside":        ["woodside"],
        "Jackson Heights": ["jackson heights"],
        "Elmhurst":        ["elmhurst"],
        "Forest Hills":    ["forest hills"],
        "Rego Park":       ["rego park"],
        "Flushing":        ["flushing"],
        "Ridgewood":       ["ridgewood"],
        "Maspeth":         ["maspeth"],
        "Bayside":         ["bayside"],
        "Jamaica":         ["jamaica"],
        "Rockaway":        ["rockaway"],
    },
    "Bronx": {
        "Riverdale":   ["riverdale"],
        "Mott Haven":  ["mott haven"],
        "South Bronx": ["south bronx"],
        "Fordham":     ["fordham"],
        "Belmont":     ["belmont"],
        "Kingsbridge": ["kingsbridge"],
        "Pelham Bay":  ["pelham bay"],
        "Parkchester": ["parkchester"],
    },
    "Staten Island": {
        "St. George": ["st. george", "st george", "saint george"],
        "Stapleton":  ["stapleton"],
    },
}

# Derived from BOROUGH_NEIGHBORHOODS — each entry adds borough-level catch-alls
# so posts that mention only "Brooklyn" still match when no specific neighborhoods are selected.
BOROUGH_KEYWORDS: dict[str, list[str]] = {
    "Brooklyn":     ["brooklyn", " bk ", "bklyn"] + [kw for kws in BOROUGH_NEIGHBORHOODS["Brooklyn"].values() for kw in kws],
    "Manhattan":    ["manhattan"]                  + [kw for kws in BOROUGH_NEIGHBORHOODS["Manhattan"].values() for kw in kws],
    "Queens":       ["queens"]                     + [kw for kws in BOROUGH_NEIGHBORHOODS["Queens"].values() for kw in kws],
    "Bronx":        ["bronx"]                      + [kw for kws in BOROUGH_NEIGHBORHOODS["Bronx"].values() for kw in kws],
    "Staten Island":["staten island"]              + [kw for kws in BOROUGH_NEIGHBORHOODS["Staten Island"].values() for kw in kws],
}

# Posts are excluded if they contain ANY of these terms (case-insensitive).
EXCLUDE_KEYWORDS: list[str] = [
    "short term",
    "short-term",
    "summer sublet",
    "entire month",
]

# How many posts to scrape per group per run
MAX_POSTS_PER_GROUP: int = 200

# Browser session storage path (keeps you logged in between runs)
SESSION_PATH: str = "session"
