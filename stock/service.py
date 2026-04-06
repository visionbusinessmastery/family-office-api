import requests
import os
from difflib import get_close_matches

FMP_API_KEY = os.getenv("FMP_API_KEY")

# Base interne (rapide)
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
}

# =========================
# SMART SEARCH
# =========================
def resolve_ticker(query: str):
    query = query.lower().strip()

    # 1. match exact
    if query in COMPANY_TO_TICKER:
        return COMPANY_TO_TICKER[query]

    # 2. fuzzy match (ex: tesl → tesla)
    match = get_close_matches(query, COMPANY_TO_TICKER.keys(), n=1, cutoff=0.6)
    if match:
        return COMPANY_TO_TICKER[match[0]]

    # 3. FMP SEARCH API (ULTRA PUISSANT)
    if FMP_API_KEY:
        try:
            url = f"https://financialmodelingprep.com/api/v3/search?query={query}&limit=1&apikey={FMP_API_KEY}"
            res = requests.get(url).json()

            if res and len(res) > 0:
                return res[0]["symbol"]

        except:
            pass

    # 4. fallback → considérer ticker direct
    return query.upper()

# =========================
# GET STOCK DATA
# =========================
def get_stock_data(query: str):

    ticker = resolve_ticker(query)

    if not FMP_API_KEY:
        return {"error": "FMP API key manquante"}

    try:
        url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={FMP_API_KEY}"
        data = requests.get(url).json()

        if not data:
            return {"error": "Aucune donnée trouvée"}

        stock = data[0]

        return {
            "name": stock.get("name"),
            "ticker": stock.get("symbol"),
            "price": stock.get("price"),
            "change_percent": stock.get("changesPercentage"),
            "market_cap": stock.get("marketCap"),
            "sector": stock.get("sector"),
            "source": "FMP"
        }

    except Exception as e:
        return {"error": str(e)}
