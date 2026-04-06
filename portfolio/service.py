from sqlalchemy import text
from database import engine
from stocks.service import get_stock_data
import requests
import time

# CACHE
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


def get_user_portfolio(user_email):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios
            WHERE user_email=:email
        """), {"email": user_email}).fetchall()

    portfolio = []
    total_value = 0
    total_cost = 0

    for r in rows:
        asset, asset_type, quantity, buy_price = r

         # =========================
        # 🔥 PRIX LIVE
        # =========================
        stock_data = get_stock_data(asset)

        current_price = stock_data.get("price") if stock_data else None

        # fallback sécurité
        if not current_price:
            current_price = buy_price

        # =========================
        # CALCULS
        # =========================
        value = quantity * current_price
        cost = quantity * buy_price
        gain = value - cost

        gain_percent = (gain / cost * 100) if cost > 0 else 0

        total_value += value
        total_cost += cost

        portfolio.append({
            "asset": asset,
            "type": asset_type,
            "quantity": quantity,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": value,
            "gain": gain,
            "gain_percent": round(gain_percent, 2),
            "source": stock_data.get("source") if stock_data else "N/A"
        })

    return {
        "portfolio": portfolio,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_gain": round(total_value - total_cost, 2),
        "total_gain_percent": round(((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0, 2)
    }
