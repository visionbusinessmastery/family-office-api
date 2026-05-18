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
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",
    "solana": "SOL-USD",
    "sol": "SOL-USD",
    "bnb": "BNB-USD",
    "xrp": "XRP-USD",
    "cardano": "ADA-USD",
    "ada": "ADA-USD",
    "dogecoin": "DOGE-USD",
    "doge": "DOGE-USD",
    "gold": "GC=F",
    "or": "GC=F",
    "xau": "GC=F",
    "silver": "SI=F",
    "argent": "SI=F",
    "oil": "CL=F",
    "petrole": "CL=F",
    "pétrole": "CL=F",
}

YAHOO_SYMBOL_SUFFIXES = ("-USD", "=F", "=X")
COMMON_CURRENCIES = {
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "CHF",
    "AUD",
    "CAD",
    "NZD",
    "TRY",
    "MXN",
    "SEK",
    "NOK",
    "DKK",
    "SGD",
    "HKD",
    "CNH",
    "ZAR",
}


def normalize_forex_symbol(query: str):
    symbol = query.strip().upper()
    compact = (
        symbol
        .replace("/", "")
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )

    if symbol.endswith("=X") and len(symbol) == 8:
        return symbol

    if len(compact) == 6:
        base = compact[:3]
        quote = compact[3:]

        if base in COMMON_CURRENCIES and quote in COMMON_CURRENCIES:
            return f"{base}{quote}=X"

    return None


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
    query_symbol = query.strip().upper()
    forex_symbol = normalize_forex_symbol(query)

    if forex_symbol:
        return forex_symbol

    # 1️⃣ direct mapping
    if query_clean in COMPANY_TO_TICKER:
        return COMPANY_TO_TICKER[query_clean]

    if query_symbol.endswith(YAHOO_SYMBOL_SUFFIXES):
        return query_symbol

    if query_symbol in COMPANY_TO_TICKER.values():
        return query_symbol

    # 2️⃣ fuzzy match
    match = get_close_matches(query_clean, COMPANY_TO_TICKER.keys(), n=1, cutoff=0.6)
    if match:
        return COMPANY_TO_TICKER[match[0]]

    if query_symbol.replace(".", "").isalnum() and 1 <= len(query_symbol) <= 6:
        return query_symbol

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
    if cached and cached.get("price") is not None:
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
            fast_info = getattr(stock, "fast_info", {}) or {}
            price = (
                fast_info.get("last_price")
                or fast_info.get("lastPrice")
                or fast_info.get("regular_market_price")
            )

            info = {}

            if not price:
                info = stock.info or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice")

            if not price:
                history = stock.history(period="1d", interval="1m")
                if not history.empty:
                    price = history["Close"].dropna().iloc[-1]

            if price:
                data = {
                    "name": info.get("shortName") if info else ticker,
                    "ticker": ticker,
                    "price": float(price),
                    "market_cap": info.get("marketCap") if info else None,
                    "sector": info.get("sector") if info else None,
                    "source": "Yahoo Finance"
                }
        except:
            pass

    if not data:
        data = {"error": "Aucune donnée disponible", "ticker": ticker}

    # Cache only usable prices so a temporary market failure does not freeze
    # portfolio gains at the purchase price.
    if data.get("price") is not None:
        set_cache(cache_key, data, ttl=60)

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
