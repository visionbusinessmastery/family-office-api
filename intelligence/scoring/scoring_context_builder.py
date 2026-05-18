# =========================
# SCORING CONTEXT BUILDER (CLEAN V3)
# =========================

import json
import hashlib

from core.cache import redis_client


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


def set_cache(key, value, ttl=600):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# SAFE GETTER
# =========================
def safe_get(data: dict, key: str, default=0):
    try:
        return data.get(key, default) if isinstance(data, dict) else default
    except:
        return default


# =========================
# HASH CONTEXT (CACHE KEY)
# =========================
def build_context_hash(user, portfolio, financial):
    raw = json.dumps(
        {
            "user": user,
            "portfolio": portfolio,
            "financial": financial
        },
        sort_keys=True
    )

    return hashlib.md5(raw.encode()).hexdigest()


# =========================
# USER CONTEXT
# =========================
def build_user_context(user: dict):
    user = user or {}

    return {
        "capital": float(safe_get(user, "capital", 0)),
        "savings": float(safe_get(user, "savings", 0)),
        "monthly_income": float(safe_get(user, "monthly_income", 0)),

        "risk_profile": (
            safe_get(user, "risk_profile", "medium") or "medium"
        ).lower(),

        "experience": safe_get(user, "experience", "low"),

        "crypto_experience": float(safe_get(user, "crypto_experience", 0)),
        "entrepreneurship_level": float(safe_get(user, "entrepreneurship_level", 0)),

        "has_business": bool(safe_get(user, "has_business", False)),
        "multiple_income_streams": bool(safe_get(user, "multiple_income_streams", False)),
        "startup_interest": bool(safe_get(user, "startup_interest", False)),
        "ai_interest": bool(safe_get(user, "ai_interest", False)),
        "business_experience": float(safe_get(user, "business_experience", 0)),
        "networking": bool(safe_get(user, "networking", False)),
    }


# =========================
# PORTFOLIO CONTEXT
# =========================
def build_portfolio_context(portfolio):
    if not isinstance(portfolio, list):
        portfolio = []

    total_value = 0
    asset_types = set()

    crypto_exposure = 0
    stocks_exposure = 0
    real_estate_exposure = 0
    forex_exposure = 0

    for asset in portfolio:
        if not isinstance(asset, dict):
            continue

        value = float(safe_get(asset, "value", 0))
        total_value += value

        asset_type = (asset.get("type") or "").lower()
        if asset_type:
            asset_types.add(asset_type)

        if asset_type == "crypto":
            crypto_exposure += value

        elif asset_type in ["stock", "stocks", "equity"]:
            stocks_exposure += value

        elif asset_type in ["real_estate", "immobilier"]:
            real_estate_exposure += value

        elif asset_type in ["forex", "currency", "currencies", "fx"]:
            forex_exposure += value

    crypto_ratio = crypto_exposure / total_value if total_value > 0 else 0

    return {
        "portfolio_value": round(total_value, 2),
        "asset_types_count": len(asset_types),
        "asset_types": list(asset_types),

        "crypto_exposure": round(crypto_exposure, 2),
        "stocks_exposure": round(stocks_exposure, 2),
        "real_estate_exposure": round(real_estate_exposure, 2),
        "forex_exposure": round(forex_exposure, 2),

        "crypto_ratio": round(crypto_ratio, 4),
    }


# =========================
# FINANCIAL CONTEXT
# =========================
def build_financial_context(financial: dict):
    financial = financial or {}

    return {
        "cashflow_score": float(safe_get(financial, "cashflow_score", 0)),
        "debt_risk_score": float(safe_get(financial, "debt_risk_score", 50)),
        "savings_velocity_score": float(safe_get(financial, "savings_velocity_score", 0)),
        "income_stability_score": float(safe_get(financial, "income_stability_score", 0)),
    }


# =========================
# MAIN CONTEXT BUILDER (ONLY ONE VERSION)
# =========================
def build_scoring_context(user=None, portfolio=None, financial=None, onboarding=None):

    user = user or {}
    portfolio = portfolio or []
    financial = financial or {}
    onboarding = onboarding or {}

    # =========================
    # CACHE KEY
    # =========================
    context_hash = build_context_hash(user, portfolio, financial)
    cache_key = f"scoring_context:{context_hash}"

    # =========================
    # CACHE HIT
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    # =========================
    # BUILD CONTEXTS
    # =========================
    user_context = build_user_context(user)
    portfolio_context = build_portfolio_context(portfolio)
    financial_context = build_financial_context(financial)

    # =========================
    # FINAL CONTEXT (FLATTENED + STRUCTURED)
    # =========================
    context = {
        # RAW
        "user": user_context,
        "portfolio": portfolio,
        "financial": financial_context,
        "onboarding": onboarding,

        # FLATTENED FAST ACCESS
        "capital": user_context["capital"],
        "savings": user_context["savings"],
        "monthly_income": user_context["monthly_income"],
        "risk_profile": user_context["risk_profile"],

        "portfolio_value": portfolio_context["portfolio_value"],
        "crypto_ratio": portfolio_context["crypto_ratio"],
        "asset_types": portfolio_context["asset_types"],
        "asset_types_count": portfolio_context["asset_types_count"],

        # ANALYTICS
        "portfolio_analytics": portfolio_context,
    }

    # =========================
    # CACHE STORE
    # =========================
    set_cache(cache_key, context, ttl=600)

    return context
