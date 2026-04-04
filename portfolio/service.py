from sqlalchemy import text
from database import engine

def get_user_portfolio(email):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios WHERE user_email=:email
        """), {"email": email})

        return result.fetchall()

# ==================================================
# STOCK DATA
# ==================================================

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

def normalize_ticker(input_value: str):
    value = input_value.lower().strip()

    # 1. vérifier si c’est un nom connu
    if value in COMPANY_TO_TICKER:
        return COMPANY_TO_TICKER[value]

    # 2. sinon considérer que c’est un ticker
    return value.upper()


def calculate_advanced_score(change_percent, pe_ratio=None):
    score = 50

    try:
        change = float(change_percent.replace("%", ""))

        if change > 3:
            score += 25
        elif change > 1:
            score += 10
        elif change < -3:
            score -= 25
        elif change < -1:
            score -= 10

        if pe_ratio:
            pe = float(pe_ratio)

            if 0 < pe < 20:
                score += 10
            elif pe > 40:
                score -= 10

    except:
        pass

    return max(0, min(score, 100))


def get_stock_data(ticker: str):

    ticker = normalize_ticker(ticker)

    # =========================
    # 1. TRY ALPHA VANTAGE
    # =========================
    if ALPHA_VANTAGE_API_KEY:

        try:
            alpha_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
            alpha_data = get_cached(alpha_url)

            alpha_quote = alpha_data.get("Global Quote", {}) if alpha_data else {}

            price = alpha_quote.get("05. price")
            change = alpha_quote.get("10. change percent")

            if price:
                return {
                    "ticker": ticker,
                    "price": float(price),
                    "change_percent": change,
                    "source": "Alpha Vantage"
                }

        except:
            pass

    # =========================
    # 2. TRY FMP
    # =========================
    if FMP_API_KEY:

        try:
            fmp_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={FMP_API_KEY}"
            fmp_data = get_cached(fmp_url)

            if fmp_data and len(fmp_data) > 0:
                stock = fmp_data[0]

                return {
                    "ticker": ticker,
                    "price": stock.get("price"),
                    "change_percent": str(stock.get("changesPercentage")) + "%",
                    "market_cap": stock.get("marketCap"),
                    "source": "FMP"
                }

        except:
            pass

    # =========================
    # 3. FINAL FALLBACK YFINANCE
    # =========================
    try:
       stock = yf.Ticker(ticker)
       info = stock.info

       price = info.get("currentPrice") or info.get("regularMarketPrice")

       if not price:
           return {
               "ticker": ticker,
               "price": None,
               "error": "price unavailable"
           }

       return {
           "ticker": ticker,
           "price": price,
           "market_cap": info.get("marketCap"),
           "pe": info.get("trailingPE"),
           "sector": info.get("sector"),
           "source": "yfinance"
       }

    except Exception as e:
        print("Stock error:", e)
        return {
            "ticker": ticker,
            "price": None,
            "error": str(e)
       }

# ==================================================
# STOCK ROUTE
# ==================================================

@app.post("/stocks/analyse")
def analyse_stock(request: StockRequest, current_user: str = Depends(get_current_user)):

    data = get_stock_data(request.ticker)

    if not data:
        raise HTTPException(status_code=400, detail="Données indisponibles")

    return data
        


