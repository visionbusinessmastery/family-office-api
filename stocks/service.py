import time
import requests
from functools import lru_cache
import os
import yfinance as yf
from difflib import get_close_matches

from core.cache import redis_client
import json


# =========================
# CONFIG
# =========================
FMP_API_KEY = os.getenv("FMP_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

REQUEST_TIMEOUT = 8


# =========================
# STATIC MAPPING
# =========================
COMPANY_TO_TICKER = {
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "apple": "AAPL",
    "amazon": "AMZN",
    "microsoft": "MSFT",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "phunware": "PHUN",
    "nike": "NKE",
}


# =========================
# CACHE HELPERS (REDIS)
# =========================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# RESOLVE TICKER
# =========================
def resolve_ticker(query: str):

    query_clean = query.lower().strip()

    # 1️⃣ direct mapping
    if query_clean in COMPANY_TO_TICKER:
        return COMPANY_TO_TICKER[query_clean]

    # 2️⃣ fuzzy match
    match = get_close_matches(query_clean, COMPANY_TO_TICKER.keys(), n=1, cutoff=0.6)
    if match:
        return COMPANY_TO_TICKER[match[0]]

    # 3️⃣ fallback search API
    results = search_stock(query_clean)

    if results and len(results) > 0:
        return results[0].get("symbol", query.upper())

    return query.upper()


# =========================
# STOCK DATA (🔥 REDIS CACHE)
# =========================
def get_stock_data(query: str):

    ticker = resolve_ticker(query)
    cache_key = f"stock:{ticker}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    data = None

    # ===== FMP =====
    if FMP_API_KEY:
        try:
            url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={FMP_API_KEY}"
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
            raw = r.json()

            if raw and isinstance(raw, list):
                stock = raw[0]

                if stock.get("price"):
                    data = {
                        "name": stock.get("name"),
                        "ticker": stock.get("symbol"),
                        "price": stock.get("price"),
                        "change_percent": stock.get("changesPercentage"),
                        "market_cap": stock.get("marketCap"),
                        "source": "FMP"
                    }
        except:
            pass

    # ===== ALPHA VANTAGE =====
    if not data and ALPHA_VANTAGE_API_KEY:
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
            quote = r.json().get("Global Quote", {})

            price = quote.get("05. price")

            if price:
                data = {
                    "ticker": ticker,
                    "price": float(price),
                    "change_percent": quote.get("10. change percent"),
                    "source": "Alpha Vantage"
                }
        except:
            pass

    # ===== YAHOO =====
    if not data:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            price = info.get("currentPrice") or info.get("regularMarketPrice")

            if price:
                data = {
                    "name": info.get("shortName"),
                    "ticker": ticker,
                    "price": price,
                    "market_cap": info.get("marketCap"),
                    "sector": info.get("sector"),
                    "source": "Yahoo Finance"
                }
        except:
            pass

    if not data:
        data = {"error": "Aucune donnée disponible", "ticker": ticker}

    # cache 5 min (market data)
    set_cache(cache_key, data, ttl=300)

    return data


# =========================
# SEARCH STOCKS (CACHE)
# =========================
def search_stock(query: str):

    cache_key = f"search:{query}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    if not FMP_API_KEY:
        return []

    try:
        url = f"https://financialmodelingprep.com/api/v3/search?query={query}&limit=5&apikey={FMP_API_KEY}"

        for attempt in range(3):
            r = requests.get(url, timeout=REQUEST_TIMEOUT)

            if r.status_code == 200:
                data = r.json()
                set_cache(cache_key, data, ttl=3600)
                return data

            if r.status_code == 429:
                time.sleep(2)

    except:
        pass

    return []


# =========================
# FAST LRU CACHE (OPTIONAL LOCAL SPEED)
# =========================
@lru_cache(maxsize=100)
def search_stock_local(query: str):
    return search_stock(query)
