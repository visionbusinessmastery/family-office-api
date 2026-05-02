import time
import requests

CACHE = {}
CACHE_DURATION = 900  # 15 min


def get(url):
    if url in CACHE and time.time() - CACHE[url]["time"] < CACHE_DURATION:
        return CACHE[url]["data"]

    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        CACHE[url] = {"data": data, "time": time.time()}
        return data

    except Exception:
        return None
