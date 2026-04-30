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
# 🔥 NORMALIZER (ANTI DOUBLONS)
# =========================
def normalize_portfolio(rows):
    """
    Merge assets by (asset + type)
    """
    merged = {}

    for r in rows:
        key = (r.asset, r.asset_type)

        if key not in merged:
            merged[key] = {
                "asset": r.asset,
                "asset_type": r.asset_type,
                "quantity": 0,
                "buy_price_total": 0,
                "count": 0
            }

        merged[key]["quantity"] += float(r.quantity or 0)
        merged[key]["buy_price_total"] += float(r.buy_price or 0)
        merged[key]["count"] += 1

    return merged.values()


# =========================
# MAIN PORTFOLIO SERVICE
# =========================
def get_user_portfolio(user_email):

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolio
            WHERE user_email=:email
        """), {"email": user_email}).fetchall()

    portfolio = []
    total_value = 0
    total_cost = 0

    # 🔥 NORMALIZE FIRST
    normalized_rows = normalize_portfolio(rows)

    for r in normalized_rows:

        asset = r["asset"]
        asset_type = r["asset_type"]
        quantity = r["quantity"]

        ticker = resolve_ticker(asset)
        stock_data = get_stock_data(ticker)

        current_price = stock_data.get("price") if stock_data else None

        if not current_price:
            current_price = r["buy_price_total"] / max(r["count"], 1)

        value = quantity * current_price
        cost = r["buy_price_total"]
        gain = value - cost

        gain_percent = (gain / cost * 100) if cost > 0 else 0

        total_value += value
        total_cost += cost

        portfolio.append({
            "asset": asset,
            "ticker": ticker,
            "type": asset_type.lower(),
            "quantity": quantity,
            "buy_price": round(cost / max(r["count"], 1), 2),
            "current_price": current_price,
            "value": round(value, 2),
            "gain": round(gain, 2),
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
