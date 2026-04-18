from portfolio.service import get_user_portfolio
from market.service import get_market
from market.scoring import calculate_ai_score
import random


# =========================
# AUTO REBALANCING ENGINE
# =========================
def generate_rebalancing(user_email):

    portfolio = get_user_portfolio(user_email)

    stocks = []
    crypto = []

    total_value = 0

    for asset in portfolio:
        total_value += asset["value"]

        # simplification classification
        if "BTC" in asset["asset"] or "ETH" in asset["asset"]:
            crypto.append(asset)
        else:
            stocks.append(asset)

    stock_weight = sum([a["value"] for a in stocks]) / total_value * 100 if total_value else 0
    crypto_weight = sum([a["value"] for a in crypto]) / total_value * 100 if total_value else 0

    # =========================
    # TARGET ALLOCATION
    # =========================
    target = {
        "stocks": 60,
        "crypto": 20,
        "cash": 20
    }

    # =========================
    # DIFFERENCE
    # =========================
    adjustments = {
        "stocks": round(target["stocks"] - stock_weight, 2),
        "crypto": round(target["crypto"] - crypto_weight, 2),
        "cash": round(target["cash"], 2)
    }

    # =========================
    # ACTIONS IA
    # =========================
    actions = []

    if stock_weight > 70:
        actions.append("Réduire exposition actions (-10% à -20%)")

    if crypto_weight > 30:
        actions.append("Prendre profits sur crypto")

    if crypto_weight < 10:
        actions.append("Renforcer crypto (DCA recommandé)")

    actions.append("Garder 20% de cash pour opportunités")

    return {
        "current_allocation": {
            "stocks": round(stock_weight, 2),
            "crypto": round(crypto_weight, 2)
        },
        "target_allocation": target,
        "adjustments": adjustments,
        "actions": actions
    }
