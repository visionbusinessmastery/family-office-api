import time
import requests
import json

from core.cache import redis_client

CACHE = {}
CACHE_DURATION = 900  # 15 min


# =========================
# LOCAL + REDIS GET
# =========================
def get(url):
    cache_key = f"http:{url}"

    # =========================
    # 1. REDIS CHECK (GLOBAL CACHE)
    # =========================
    try:
        if redis_client:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
    except:
        pass

    # =========================
    # 2. LOCAL CACHE (FAST LAYER)
    # =========================
    if cache_key in CACHE and time.time() - CACHE[cache_key]["time"] < CACHE_DURATION:
        return CACHE[cache_key]["data"]

    # =========================
    # 3. API CALL
    # =========================
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()

        # =========================
        # SAVE LOCAL CACHE
        # =========================
        CACHE[cache_key] = {
            "data": data,
            "time": time.time()
        }

        # =========================
        # SAVE REDIS CACHE (GLOBAL)
        # =========================
        try:
            if redis_client:
                redis_client.setex(cache_key, CACHE_DURATION, json.dumps(data))
        except:
            pass

        return data

    except Exception:
        return None
