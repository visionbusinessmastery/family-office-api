from sqlalchemy import text
from database import engine
from stocks.service import get_stock_data, resolve_ticker
import requests
import time

# =========================
# CACHE PRICES
# =========================
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

    except Exception:
        return None


# =========================
# MAIN PORTFOLIO SERVICE
# =========================
def get_user_portfolio(user_email):

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_email=:email
        """), {"email": user_email}).fetchall()

    portfolio = []
    total_value = 0
    total_cost = 0

    for r in rows:

        asset = r.asset_name
        asset_type = r.category
        quantity = float(r.quantity or 0)
        purchase_price = float(r.purchase_price or 0)

        ticker = resolve_ticker(asset)
        stock_data = get_stock_data(ticker)

        current_price = stock_data.get("price") if stock_data else None

        if not current_price:
            current_price = purchase_price

        value = quantity * current_price
        cost = quantity * purchase_price
        gain = value - cost
        gain_percent = (gain / cost * 100) if cost > 0 else 0

        total_value += value
        total_cost += cost

        portfolio.append({
            "id": r.id,  # 🔥 FIX CRUCIAL FRONTEND DELETE
            "asset_name": asset,
            "asset_type": asset_type,
            "quantity": quantity,
            "purchase_price": purchase_price,
            "current_price": current_price,
            "value": round(value, 2),
            "gain": round(gain, 2),
            "gain_percent": round(gain_percent, 2),
            "ticker": ticker,
            "source": stock_data.get("source") if stock_data else "N/A"
        })

    return {
        "portfolio": portfolio,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_gain": round(total_value - total_cost, 2),
        "total_gain_percent": round(((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0, 2)
    }
