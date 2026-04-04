from sqlalchemy import text
from database import engine
import yfinance as yf

# ==================================================
# CONFIG STOCK & PORTFOLIO
# ==================================================

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

# ==================================================
# GET USER PORTFOLIO
# ==================================================
def get_user_portfolio(email):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios WHERE user_email=:email
        """), {"email": email})

        return result.fetchall()

    portfolio = []
    total_value = 0
    total_cost = 0

    for r in rows:
        asset = r[0]
        asset_type = r[1]
        quantity = r[2]
        buy_price = r[3]

        ticker = normalize_ticker(asset)
        data = get_stock_data(ticker)

        # 🔥 TON BLOC (BON ENDROIT)
        if not data or not data.get("price"):
            current_price = None
            value = 0
            performance = 0
            status = "invalid"
        else:
            current_price = data["price"]
            value = quantity * current_price
            performance = ((current_price - buy_price) / buy_price) * 100
            status = "ok"

        cost = quantity * buy_price

        total_value += value
        total_cost += cost

        portfolio.append({
            "asset": asset,
            "type": asset_type,
            "quantity": quantity,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": round(value, 2),
            "performance": round(performance, 2),
            "status": status
        })

    total_performance = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

    return {
        "portfolio": portfolio,
        "summary": {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_performance": round(total_performance, 2)
        }
    }

# ==================================================
# CACHE
# ==================================================

cache = {}
CACHE_DURATION = 900

def get_cached(url):
    if url in cache and time.time() - cache[url]["time"] < CACHE_DURATION:
        return cache[url]["data"]

    try:
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        cache[url] = {"data": data, "time": time.time()}
        return data

    except:
        return None

