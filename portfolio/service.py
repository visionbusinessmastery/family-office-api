# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine
from stocks.service import get_stock_data, resolve_ticker

from core.cache import redis_client
import json


# =========================
# SAFE CACHE HELPERS
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


def set_cache(key, value, ttl=900):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# PORTFOLIO ENGINE (OPTIMIZED + CACHE)
# =========================
def get_user_portfolio(user_email: str):

    cache_key = f"portfolio:{user_email}"

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    with engine.begin() as conn:

        rows = conn.execute(text("""
            SELECT id, asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_email = :email
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

            # =========================
            # STOCK DATA SAFE CALL
            # =========================
            stock_data = get_stock_data(ticker) or {}

            current_price = stock_data.get("price") or purchase_price

            value = quantity * current_price
            cost = quantity * purchase_price
            gain = value - cost

            # =========================
            # SAFE DIVISION
            # =========================
            if cost > 0:
                gain_percent = (gain / cost) * 100
            else:
                gain_percent = 0

            total_value += value
            total_cost += cost

            portfolio.append({
                "id": r.id,
                "asset_name": asset,
                "asset_type": asset_type,
                "quantity": quantity,
                "purchase_price": purchase_price,
                "current_price": current_price,
                "value": round(value, 2),
                "gain": round(gain, 2),
                "gain_percent": round(gain_percent, 2),
                "ticker": ticker,
                "source": stock_data.get("source", "N/A")
            })

        result = {
            "portfolio": portfolio,
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_gain": round(total_value - total_cost, 2),
            "total_gain_percent": round(
                ((total_value - total_cost) / total_cost * 100)
                if total_cost > 0 else 0,
                2
            )
        }

    # =========================
    # CACHE STORE
    # =========================
    set_cache(cache_key, result, ttl=900)

    return result


# =========================
# PORTFOLIO SNAPSHOT
# =========================
def save_portfolio_snapshot(user_id: int):

    with engine.begin() as conn:

        total = conn.execute(text("""
            SELECT COALESCE(SUM(quantity * purchase_price), 0)
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": user_id}).scalar()

        conn.execute(text("""
            INSERT INTO portfolio_history (user_id, total_value, created_at)
            VALUES (:user_id, :total, NOW())
        """), {
            "user_id": user_id,
            "total": float(total or 0)
        })
