# =========================
# EXECUTION ENGINE V4
# =========================

from sqlalchemy import text
from database import engine
import random

# =========================
# EXECUTION ENGINE V4
# =========================

from advisor.autopilot_v4_engine import AutopilotV4

# =========================
# SINGLETON ENGINE
# =========================
_autopilot = AutopilotV4()


# =========================
# MAIN EXECUTION WRAPPER
# =========================
def execute_autopilot_actions(
    portfolio,
    market_signal=0.5,
    symbol="BTC",
    price=100
):

    """
    Bridge compatible avec service.py
    """

    return _autopilot.run(
        portfolio=portfolio,
        market_signal=market_signal,
        symbol=symbol,
        price=price
    )
    
def get_price(asset, market):
    return float(market.get(asset, random.uniform(100, 50000)))


def simulate_trade(user_email, action, asset, amount, market):

    price = get_price(asset, market)
    value = round(amount * price, 2)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO simulated_trades (
                user_email, action, asset, amount, price, value
            )
            VALUES (:email, :action, :asset, :amount, :price, :value)
        """), {
            "email": user_email,
            "action": action,
            "asset": asset,
            "amount": amount,
            "price": price,
            "value": value
        })

    return {
        "action": action,
        "asset": asset,
        "amount": amount,
        "price": price,
        "value": value
    }


def execute_actions(user_email, actions, market):

    trades = []

    for action in actions:

        if action == "REBALANCE":
            trades.append(simulate_trade(user_email, "SELL", "BTC", 0.1, market))

        elif action == "REDUCE_RISK":
            trades.append(simulate_trade(user_email, "SELL", "ETH", 0.3, market))

        elif action == "AGGRESSIVE_GROWTH":
            trades.append(simulate_trade(user_email, "BUY", "NASDAQ", 1, market))

    return trades
