import requests
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
}

# =========================
# SMART SEARCH
# =========================
def resolve_ticker(query: str):
    query = query.lower().strip()

    if query in COMPANY_TO_TICKER:
        return COMPANY_TO_TICKER[query]

    match = get_close_matches(query, COMPANY_TO_TICKER.keys(), n=1, cutoff=0.6)
    if match:
        return COMPANY_TO_TICKER[match[0]]

    return query.upper()

# =========================
# GET STOCK DATA (MULTI SOURCE)
# =========================
def get_stock_data(query: str):

    ticker = resolve_ticker(query)

    # =========================
    # 1. FMP (BEST)
    # =========================
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
        except:
            pass

    # =========================
    # 2. ALPHA VANTAGE
    # =========================
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
        except:
            pass

    # =========================
    # 3. YAHOO FINANCE (ULTIMATE BACKUP)
    # =========================
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
