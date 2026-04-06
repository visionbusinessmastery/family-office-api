from sqlalchemy import text
from database import engine
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

        # ⚠️ simplifié (pas encore API stock)
        current_price = buy_price
        value = quantity * current_price
        cost = quantity * buy_price

        total_value += value
        total_cost += cost

        portfolio.append({
            "asset": asset,
            "type": asset_type,
            "quantity": quantity,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": value
        })

    return {
        "portfolio": portfolio,
        "total_value": total_value,
        "total_cost": total_cost
    }
