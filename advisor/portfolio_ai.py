import json


# =========================
# SCORE PORTFOLIO
# =========================
def score_portfolio(portfolio: dict, market: dict):

    # simplification hedge fund style
    risk_score = 50
    diversification_score = 50
    performance_score = 50

    assets = portfolio.get("assets", [])

    if len(assets) > 5:
        diversification_score += 20
    if len(assets) < 2:
        diversification_score -= 30

    # mock performance analysis
    if market.get("trend") == "bullish":
        performance_score += 20
    elif market.get("trend") == "bearish":
        performance_score -= 20

    total_score = (
        risk_score * 0.3 +
        diversification_score * 0.3 +
        performance_score * 0.4
    )

    return {
        "risk_score": risk_score,
        "diversification_score": diversification_score,
        "performance_score": performance_score,
        "total_score": round(total_score, 2)
    }


# =========================
# DECISION ENGINE
# =========================
def generate_actions(score: dict):

    actions = []

    if score["total_score"] < 40:
        actions.append("REBALANCE_PORTFOLIO")
        actions.append("REDUCE_RISK_EXPOSURE")

    elif score["total_score"] < 70:
        actions.append("OPTIMIZE_ALLOCATION")
        actions.append("PARTIAL_REBALANCE")

    else:
        actions.append("HOLD")
        actions.append("INCREASE_GROWTH_EXPOSURE")

    return actions


# =========================
# TARGET ALLOCATION ENGINE
# =========================
def optimal_allocation(risk_level: str):

    base = {
        "low": {"stocks": 25, "real_estate": 40, "crypto": 5, "business": 20, "cash": 10},
        "medium": {"stocks": 35, "real_estate": 25, "crypto": 15, "business": 20, "cash": 5},
        "high": {"stocks": 30, "real_estate": 10, "crypto": 35, "business": 20, "cash": 5},
    }

    return base.get(risk_level, base["medium"])
