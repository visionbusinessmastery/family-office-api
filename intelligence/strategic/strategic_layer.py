# =========================
# STRATEGIC INTELLIGENCE LAYER
# intelligence/strategic/strategic_layer.py
# =========================

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# =========================
# RISK ENGINE
# =========================
def compute_risk_engine(context):

    risk_score = 0

    debt_ratio = context.get("debt_ratio", 0)
    savings = context.get("savings", 0)
    monthly_income = context.get("monthly_income", 0)
    diversification = context.get("diversification", 0)

    # DETTES
    if debt_ratio > 0.6:
        risk_score += 40

    elif debt_ratio > 0.3:
        risk_score += 20

    # ÉPARGNE
    if savings < monthly_income * 3:
        risk_score += 30

    # DIVERSIFICATION
    if diversification < 3:
        risk_score += 30

    risk_score = min(risk_score, 100)

    if risk_score >= 70:
        level = "HIGH"

    elif risk_score >= 40:
        level = "MEDIUM"

    else:
        level = "LOW"

    return {
        "risk_score": risk_score,
        "risk_level": level,
    }


# =========================
# WEALTH ENGINE
# =========================
def compute_wealth_engine(context):

    capital = context.get("capital", 0)
    portfolio_value = context.get("portfolio_value", 0)
    monthly_income = context.get("monthly_income", 0)
    savings = context.get("savings", 0)

    wealth_score = 0

    wealth_score += min(capital / 1000, 40)
    wealth_score += min(portfolio_value / 2000, 30)
    wealth_score += min(monthly_income / 200, 20)
    wealth_score += min(savings / 1000, 10)

    wealth_score = int(min(wealth_score, 100))

    if wealth_score >= 80:
        tier = "ULTRA HIGH"

    elif wealth_score >= 60:
        tier = "HIGH"

    elif wealth_score >= 40:
        tier = "MEDIUM"

    else:
        tier = "GROWTH"

    return {
        "wealth_score": wealth_score,
        "wealth_tier": tier,
    }


# =========================
# DIVERSIFICATION ENGINE
# =========================
def compute_diversification_engine(context):

    asset_types = context.get("asset_types", [])

    unique_assets = len(set(asset_types))

    diversification_score = min(unique_assets * 15, 100)

    if diversification_score >= 80:
        profile = "HIGHLY DIVERSIFIED"

    elif diversification_score >= 50:
        profile = "BALANCED"

    else:
        profile = "CONCENTRATED"

    return {
        "diversification_score": diversification_score,
        "diversification_profile": profile,
    }


# =========================
# ALLOCATION ENGINE
# =========================
def compute_allocation_engine(context):

    allocations = {
        "stocks": 35,
        "etf": 25,
        "real_estate": 20,
        "cash": 10,
        "crypto": 5,
        "commodities": 5,
    }

    risk_profile = context.get("risk_profile", "medium")

    if risk_profile == "high":

        allocations["crypto"] = 15
        allocations["cash"] = 5

    elif risk_profile == "low":

        allocations["cash"] = 20
        allocations["crypto"] = 2

    return {
        "recommended_allocation": allocations
    }


# =========================
# MACRO ENGINE
# =========================
def compute_macro_engine():

    current_year = datetime.utcnow().year

    macro = {
        "interest_rates": "HIGH",
        "inflation": "MODERATE",
        "market_cycle": "EXPANSION",
        "real_estate_cycle": "SLOWDOWN",
        "crypto_cycle": "VOLATILE",
        "year": current_year,
    }

    return macro


# =========================
# PREDICTION ENGINE
# =========================
def compute_prediction_engine(context):

    monthly_income = context.get("monthly_income", 0)
    savings_rate = context.get("savings_rate", 0.1)

    projected_1y = monthly_income * 12 * savings_rate
    projected_5y = projected_1y * 5 * 1.5
    projected_10y = projected_5y * 2.2

    return {
        "1_year_projection": int(projected_1y),
        "5_year_projection": int(projected_5y),
        "10_year_projection": int(projected_10y),
    }


# =========================
# ASSET RECOMMENDATION ENGINE
# =========================
def compute_asset_recommendation_engine(context):

    recommendations = []

    risk = context.get("risk_profile", "medium")
    capital = context.get("capital", 0)

    if capital < 5000:

        recommendations.append(
            "Commencer avec des ETF diversifiés"
        )

        recommendations.append(
            "Construire un fonds de sécurité"
        )

    if risk == "high":

        recommendations.append(
            "Allocation crypto spéculative contrôlée"
        )

        recommendations.append(
            "Actions croissance IA"
        )

    if risk == "low":

        recommendations.append(
            "Obligations et immobilier"
        )

    recommendations.append(
        "Diversification multi-assets internationale"
    )

    return {
        "recommended_assets": recommendations
    }


# =========================
# MASTER STRATEGIC LAYER
# =========================
def compute_strategic_intelligence(context):

    try:

        risk_engine = compute_risk_engine(context)

        wealth_engine = compute_wealth_engine(context)

        diversification_engine = (
            compute_diversification_engine(context)
        )

        allocation_engine = (
            compute_allocation_engine(context)
        )

        macro_engine = compute_macro_engine()

        prediction_engine = (
            compute_prediction_engine(context)
        )

        recommendation_engine = (
            compute_asset_recommendation_engine(context)
        )

        strategic_score = int(
            (
                wealth_engine["wealth_score"]
                + diversification_engine["diversification_score"]
                + (100 - risk_engine["risk_score"])
            ) / 3
        )

        return {

            # GLOBAL STRATEGIC SCORE
            "strategic_score": strategic_score,

            # ENGINES
            "risk_engine": risk_engine,

            "wealth_engine": wealth_engine,

            "diversification_engine":
                diversification_engine,

            "allocation_engine":
                allocation_engine,

            "macro_engine":
                macro_engine,

            "prediction_engine":
                prediction_engine,

            "asset_recommendation_engine":
                recommendation_engine,
        }

    except Exception as e:

        logger.error(
            f"[STRATEGIC LAYER ERROR] {e}"
        )

        return {
            "strategic_score": 0,
            "error": str(e),
        }
