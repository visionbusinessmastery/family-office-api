import json

from core.cache import redis_client
from opportunity_cache.fingerprint import opportunity_fingerprint
from opportunity_cache.ttl_registry import ttl_for_universe


def build_opportunity_cache_key(universe: str, payload: dict):
    return f"opportunity_cache:{universe}:{opportunity_fingerprint(payload)}"


def get_cached_opportunities(universe: str, payload: dict):
    key = build_opportunity_cache_key(universe, payload)
    try:
        if redis_client:
            value = redis_client.get(key)
            return json.loads(value) if value else None
    except Exception:
        return None
    return None


def set_cached_opportunities(universe: str, payload: dict, value: dict):
    key = build_opportunity_cache_key(universe, payload)
    try:
        if redis_client:
            redis_client.setex(
                key,
                ttl_for_universe(universe),
                json.dumps(value, default=str),
            )
            return True
    except Exception:
        return False
    return False
