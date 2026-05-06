# =========================
# PERFORMANCE ENGINE V4
# =========================

from sqlalchemy import text
from database import engine


def get_user_trades(user_email):

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT action, asset, amount, price, value
            FROM simulated_trades
            WHERE user_email = :email
        """), {"email": user_email}).fetchall()

    return [dict(r._mapping) for r in rows]


def compute_performance(user_email):

    trades = get_user_trades(user_email)

    if not trades:
        return {
            "total_trades": 0,
            "total_value": 0,
            "roi": 0,
            "drawdown": 0
        }

    total_value = sum(t["value"] for t in trades)

    buys = sum(t["value"] for t in trades if t["action"] == "BUY")
    sells = sum(t["value"] for t in trades if t["action"] == "SELL")

    pnl = sells - buys
    roi = (pnl / (buys + 1)) * 100

    drawdown = min(0, pnl)

    return {
        "total_trades": len(trades),
        "total_value": round(total_value, 2),
        "pnl": round(pnl, 2),
        "roi": round(roi, 2),
        "drawdown": round(drawdown, 2)
    }
