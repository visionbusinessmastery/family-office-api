# =========================
# SCORING CONTEXT BUILDER
# =========================

from typing import Dict, List, Any


# =========================
# SAFE GETTER
# =========================
def safe_get(data: dict, key: str, default=0):
    try:
        return data.get(key, default) if isinstance(data, dict) else default
    except Exception:
        return default


# =========================
# NORMALIZE USER PROFILE
# =========================
def build_user_context(user: dict) -> dict:

    return {
        "capital": safe_get(user, "capital", 0),
        "savings": safe_get(user, "savings", 0),
        "monthly_income": safe_get(user, "monthly_income", 0),
        "risk_profile": (safe_get(user, "risk_profile", "medium") or "medium").lower(),
        "experience": safe_get(user, "experience", "low"),
        "crypto_experience": safe_get(user, "crypto_experience", 0),
        "entrepreneurship_level": safe_get(user, "entrepreneurship_level", 0),

        "has_business": safe_get(user, "has_business", False),
        "multiple_income_streams": safe_get(user, "multiple_income_streams", False),
        "startup_interest": safe_get(user, "startup_interest", False),
        "ai_interest": safe_get(user, "ai_interest", False),
        "business_experience": safe_get(user, "business_experience", 0),
        "networking": safe_get(user, "networking", False),
    }


# =========================
# NORMALIZE PORTFOLIO
# =========================
def build_portfolio_context(portfolio: List[dict]) -> dict:

    if not isinstance(portfolio, list):
        portfolio = []

    total_value = 0
    asset_types = set()
    crypto_exposure = 0

    for asset in portfolio:

        if not isinstance(asset, dict):
            continue

        value = safe_get(asset, "value", 0)
        total_value += value

        asset_type = (asset.get("type") or "").lower()
        if asset_type:
            asset_types.add(asset_type)

        if asset_type == "crypto":
            crypto_exposure += value

    return {
        "total_portfolio_value": total_value,
        "asset_types_count": len(asset_types),
        "asset_types": list(asset_types),
        "crypto_exposure": crypto_exposure,
        "crypto_ratio": (crypto_exposure / total_value) if total_value > 0 else 0,
    }


# =========================
# NORMALIZE FINANCIAL DATA
# =========================
def build_financial_context(financial: dict) -> dict:

    financial = financial or {}

    return {
        "cashflow_score": safe_get(financial, "cashflow_score", 0),
        "debt_risk_score": safe_get(financial, "debt_risk_score", 50),
        "savings_velocity_score": safe_get(financial, "savings_velocity_score", 0),
        "income_stability_score": safe_get(financial, "income_stability_score", 0),
    }


# =========================
# GLOBAL CONTEXT BUILDER
# =========================
def build_scoring_context(
    user: dict = None,
    portfolio: list = None,
    financial: dict = None
) -> dict:

    user = user or {}
    portfolio = portfolio or []
    financial = financial or {}

    return {
        "user": build_user_context(user),
        "portfolio": build_portfolio_context(portfolio),
        "financial": build_financial_context(financial),
    }
