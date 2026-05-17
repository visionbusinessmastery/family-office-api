import time
import json
import hashlib
import requests
import logging

from core.cache import redis_client


CACHE = {}
CACHE_DURATION = 900  # 15 min
logger = logging.getLogger(__name__)


# =========================
# CACHE KEY NORMALIZER
# =========================
def make_cache_key(url: str):
    return "http:" + hashlib.md5(url.encode()).hexdigest()


# =========================
# SAFE REQUEST WITH CACHE
# =========================
def get(url):
    cache_key = make_cache_key(url)

    # =========================
    # 1. REDIS CACHE (GLOBAL)
    # =========================
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning("Redis read error: %s", e)

    # =========================
    # 2. LOCAL CACHE (FAST LAYER)
    # =========================
    cached_local = CACHE.get(cache_key)

    if cached_local:
        if time.time() - cached_local["time"] < CACHE_DURATION:
            return cached_local["data"]

    # =========================
    # 3. API CALL
    # =========================
    try:
        response = requests.get(url, timeout=10)

        if not response.ok:
            return None

        data = response.json()

        # =========================
        # LOCAL CACHE STORE
        # =========================
        CACHE[cache_key] = {
            "data": data,
            "time": time.time()
        }

        # =========================
        # REDIS STORE
        # =========================
        if redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    CACHE_DURATION,
                    json.dumps(data)
                )
            except Exception as e:
                logger.warning("Redis write error: %s", e)

        return data

    except requests.RequestException as e:
        logger.warning("HTTP cache fetch error: %s", e)
        return None
