ZONES = {
    "cyphoma": {
        "martinique": "martinique",
        "guadeloupe": "guadeloupe",
        "guyane": "guyane",
        "saint-martin": "saint-martin"
    },
    "97immo": {
        "martinique": "martinique",
        "guadeloupe": "guadeloupe",
        "guyane": "guyane"
    }
}

SCRAPER_LIMIT = 20

SCRAPER_MATRIX = {
    "martinique": ["cyphoma", "97immo", "leboncoin"],
    "guadeloupe": ["cyphoma", "97immo", "leboncoin"],
    "guyane": ["cyphoma", "leboncoin"],
    "reunion": ["leboncoin", "seloger"],
    "polynesie": ["leboncoin"]
}
