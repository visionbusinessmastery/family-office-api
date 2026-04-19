import time
import requests
from functools import lru_cache
import os
import yfinance as yf
from difflib import get_close_matches

FMP_API_KEY = os.getenv("FMP_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

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
    "nike": "NKE",  # 🔥 AJOUT IMPORTANT
}

# =========================
# SMART SEARCH (AMÉLIORÉ)
# =========================
def resolve_ticker(query: str):
    query_clean = query.lower().strip()

    # 1️⃣ mapping direct
    if query_clean in COMPANY_TO_TICKER:
        return COMPANY_TO_TICKER[query_clean]

    # 2️⃣ fuzzy match (tolérance fautes)
    match = get_close_matches(query_clean, COMPANY_TO_TICKER.keys(), n=1, cutoff=0.6)
    if match:
        return COMPANY_TO_TICKER[match[0]]

    # 3️⃣ 🔥 fallback FMP search (NOUVEAU)
    try:
        results = search_stock_cached(query_clean)

        if results and len(results) > 0:
            return results[0].get("symbol", query_clean.upper())
    except Exception:
        pass

    # 4️⃣ fallback final
    return query.upper()


# =========================
# GET STOCK DATA
# =========================
def get_stock_data(query: str):

    ticker = resolve_ticker(query)

    # ===== FMP =====
    if FMP_API_KEY:
        try:
            url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={FMP_API_KEY}"
            data = requests.get(url).json()

            if data and len(data) > 0:
                stock = data[0]

                if stock.get("price"):
                    return {
                        "name": stock.get("name"),
                        "ticker": stock.get("symbol"),
                        "price": stock.get("price"),
                        "change_percent": stock.get("changesPercentage"),
                        "market_cap": stock.get("marketCap"),
                        "source": "FMP"
                    }
        except Exception:
            pass

    # ===== ALPHA VANTAGE =====
    if ALPHA_VANTAGE_API_KEY:
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
            data = requests.get(url).json()

            quote = data.get("Global Quote", {})
            price = quote.get("05. price")

            if price:
                return {
                    "ticker": ticker,
                    "price": float(price),
                    "change_percent": quote.get("10. change percent"),
                    "source": "Alpha Vantage"
                }
        except Exception:
            pass

    # ===== YAHOO =====
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        price = info.get("currentPrice") or info.get("regularMarketPrice")

        if price:
            return {
                "name": info.get("shortName"),
                "ticker": ticker,
                "price": price,
                "market_cap": info.get("marketCap"),
                "pe": info.get("trailingPE"),
                "sector": info.get("sector"),
                "source": "Yahoo Finance"
            }

    except Exception as e:
        return {"error": str(e)}

    return {"error": "Aucune donnée disponible"}


# =========================
# INTELLIGENCE
# =========================
def get_stock_intelligence(query):

    symbol = query.symbol if hasattr(query, "symbol") else query

    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        return {
            "symbol": symbol,
            "price": info.get("currentPrice"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "sector": info.get("sector"),
            "recommendation": "buy" if (info.get("trailingPE") or 0) < 20 else "hold"
        }

    except Exception as e:
        return {
            "error": str(e),
            "symbol": symbol
        }


# =========================
# SEARCH (CACHE)
# =========================
@lru_cache(maxsize=100)
def search_stock_cached(query: str):

    if not FMP_API_KEY:
        return []

    url = f"https://financialmodelingprep.com/api/v3/search?query={query}&limit=5&apikey={FMP_API_KEY}"
    
    for attempt in range(3):
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        
        elif response.status_code == 429:
            time.sleep(2)
        
    return []
