TTL_BY_UNIVERSE = {
    "real_estate": 6 * 60 * 60,
    "investments": 30 * 60,
    "business": 12 * 60 * 60,
    "franchise": 24 * 60 * 60,
    "market": 30 * 60,
}


def ttl_for_universe(universe: str):
    return TTL_BY_UNIVERSE.get(str(universe or "").lower(), 30 * 60)
