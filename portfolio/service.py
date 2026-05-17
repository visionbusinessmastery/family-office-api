# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine
from stocks.service import get_stock_data, resolve_ticker

from core.cache import redis_client
import json


# =========================
# CACHE HELPERS
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


def invalidate_portfolio_cache(user_id: int, email: str = None):
    try:
        if redis_client:
            keys = [
                f"portfolio:{user_id}",
                f"cmd_center:{user_id}",
            ]

            if email:
                keys.extend([
                    f"intel:{email}",
                    f"context:{email}",
                    f"score:{email}",
                ])

            redis_client.delete(*keys)
    except:
        pass


# =========================
# STOCK CACHE (🔥 NEW - IMPORTANT)
# =========================
def get_stock_cached(ticker: str):
    cache_key = f"stock:{ticker}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    data = get_stock_data(ticker) or {}

    # cache prix 5 min (market data change souvent)
    set_cache(cache_key, data, ttl=300)

    return data


def build_portfolio_payload(rows):
    portfolio = []
    total_value = 0
    total_cost = 0

    for r in rows:

        asset = r.asset_name
        asset_type = r.category
        quantity = float(r.quantity or 0)
        purchase_price = float(r.purchase_price or 0)

        ticker = resolve_ticker(asset)
        stock_data = get_stock_cached(ticker)
        current_price = stock_data.get("price") or purchase_price

        value = quantity * current_price
        cost = quantity * purchase_price
        gain = value - cost
        gain_percent = (gain / cost * 100) if cost > 0 else 0

        total_value += value
        total_cost += cost

        portfolio.append({
            "id": r.id,
            "asset_name": asset,
            "asset_type": asset_type,
            "quantity": quantity,
            "purchase_price": purchase_price,
            "current_price": current_price,
            "current_value": round(value, 2),
            "value": round(value, 2),
            "cost": round(cost, 2),
            "gain": round(gain, 2),
            "gain_percent": round(gain_percent, 2),
            "ticker": ticker,
            "source": stock_data.get("source", "N/A")
        })

    total_gain = total_value - total_cost

    return {
        "portfolio": portfolio,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_gain": round(total_gain, 2),
        "total_gain_percent": round(
            (total_gain / total_cost * 100) if total_cost > 0 else 0,
            2
        )
    }


# =========================
# PORTFOLIO ENGINE (OPTIMIZED + CACHE)
# =========================
def get_user_portfolio(user_id: int):

    cache_key = f"portfolio:{user_id}"

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
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()

        result = build_portfolio_payload(rows)

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

        rows = conn.execute(text("""
            SELECT id, asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()

        snapshot = build_portfolio_payload(rows)

        conn.execute(text("""
            INSERT INTO portfolio_history (user_id, total_value, created_at)
            VALUES (:user_id, :total, NOW())
        """), {
            "user_id": user_id,
            "total": float(snapshot.get("total_value") or 0)
        })


def enrich_portfolio_with_ai(portfolio):

    enriched = []

    for asset in portfolio:

        ticker = asset.get("asset")

        news = get_market_news(ticker) or []

        sentiment_result = analyze_sentiment(news) or {}

        sentiment_score = (
            sentiment_result.get("score", 50)
            if isinstance(sentiment_result, dict)
            else 50
        )

        trend_score = get_trends(ticker)

        price_change = asset.get("price_change", 0)

        score = calculate_ai_score(
            sentiment_score,
            trend_score,
            price_change
        )

        enriched.append({
            **asset,
            "ai_score": score,
            "signal": get_signal(score),
            "risk": get_risk(score),
            "sentiment_score": sentiment_score,
            "trend_score": trend_score
        })

    return enriched
