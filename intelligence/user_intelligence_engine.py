# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine
import json

from intelligence.core.upgrade_engine import compute_upgrade_decision
from intelligence.strategic.feature_engine import compute_feature_access
from intelligence.strategic.opportunity_engine import compute_opportunities
from intelligence.strategic.strategic_layer import compute_strategic_layer
from intelligence.scoring.financial_overview import get_user_financial_overview
from intelligence.scoring.family_office_score import compute_family_office_score

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


def set_cache(key, value, ttl=60):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# SAFE GETTER
# =========================
def safe_get(obj, key, default=0):
    try:
        return obj.get(key, default) if isinstance(obj, dict) else default
    except:
        return default


# =========================
# LEVEL SYSTEM
# =========================
def compute_level(score_value: int, plan: str = "FREE"):

    plan = (plan or "FREE").upper()

    if plan == "LIBERTY":
        return "LIBERTY"

    if score_value >= 15000:
        return "LIBERTY"
    elif score_value >= 7000:
        return "ELITE"
    elif score_value >= 3000:
        return "ELITE"
    elif score_value >= 1000:
        return "GOLD"
    elif score_value >= 40:
        return "SILVER"
    else:
        return "FREE"


# =========================
# MAIN ENGINE
# =========================
def compute_user_intelligence(user_email: str):

    cache_key = f"intel:{user_email}"
    context_cache_key = f"context:{user_email}"

    # =========================
    # GLOBAL CACHE (FAST RETURN)
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    with engine.begin() as conn:

        # =========================
        # USER FETCH
        # =========================
        user = conn.execute(text("""
            SELECT id, email, plan, profile_completed,
                   revenus_mensuels, charges_mensuelles
            FROM users
            WHERE email = :email
        """), {"email": user_email}).fetchone()

        if not user:
            return {"error": "user not found"}

        # =========================
        # ONBOARDING CHECK
        # =========================
        if not user.profile_completed:

            result = {
                "state": "ONBOARDING_REQUIRED",
                "score": {"score": 0},
                "level": "ONBOARDING",
                "features": [],
                "opportunities": [],
                "upgrade": None
            }

            set_cache(cache_key, result, ttl=30)
            return result

        # =========================
        # CONTEXT CACHE (PROFILE + ONBOARDING)
        # =========================
        context = get_cache(context_cache_key)

        if context:
            profile_dict = context["profile"]
            onboarding = context["onboarding"]

        else:
            profile = conn.execute(text("""
                SELECT *
                FROM user_profiles
                WHERE user_email = :email
            """), {"email": user_email}).fetchone()

            profile_dict_raw = dict(profile._mapping) if profile else {}

            onboarding = {
                "monthly_income": float(user.revenus_mensuels or 0),
                "monthly_expenses": float(user.charges_mensuelles or 0),
                "savings": float(profile_dict_raw.get("savings") or 0),
                "debts": float(profile_dict_raw.get("debts") or 0),
            }

            profile_dict = {
                "savings": onboarding["savings"],
                "investments": float(profile_dict_raw.get("investments") or 0),
                "risk_profile": (profile_dict_raw.get("risk_profile") or "medium").lower(),
                "monthly_income": onboarding["monthly_income"],
                "debt": onboarding["debts"],
                "email": user.email,
                "plan": user.plan,
            }

            set_cache(context_cache_key, {
                "profile": profile_dict,
                "onboarding": onboarding
            }, ttl=300)

        # =========================
        # PORTFOLIO
        # =========================
        rows = conn.execute(text("""
            SELECT asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": user.id}).fetchall()

        portfolio_list = []
        total_portfolio_value = 0

        for p in rows:
            qty = float(p.quantity or 0)
            price = float(p.purchase_price or 0)
            value = qty * price

            total_portfolio_value += value

            portfolio_list.append({
                "asset_name": p.asset_name,
                "type": (p.category or "").lower(),
                "value": value
            })

        profile_dict["portfolio_value"] = total_portfolio_value

        if profile_dict["investments"] == 0:
            profile_dict["investments"] = total_portfolio_value

        # =========================
        # FINANCIAL OVERVIEW
        # =========================
        financial = get_user_financial_overview(user.id) or {}
        totals = financial.get("totals", {}) if isinstance(financial, dict) else {}

        financial_features = {
            "cashflow_score": safe_get(totals, "net_cashflow", 0),
            "monthly_income": onboarding["monthly_income"],
            "monthly_expenses": onboarding["monthly_expenses"],
            "debt_risk_score": safe_get(totals, "total_debt", 0),
            "savings_velocity_score": safe_get(totals, "total_savings", 0),
            "income_stability_score": len(financial.get("income_sources", [])) * 10,
            "raw": totals
        } if totals else {}

        # =========================
        # SCORE ENGINE
        # =========================
        score_result = compute_family_office_score(
            profile_dict,
            portfolio_list,
            financial_features
        ) or {}

        score_value = int(safe_get(score_result, "score", 0))

        # =========================
        # LEVEL + FEATURES
        # =========================
        level = compute_level(score_value, user.plan)

        upgrade = compute_upgrade_decision(user.plan, score_value)
        features = compute_feature_access(profile_dict, {"score": score_value})
        opportunities = compute_opportunities(profile_dict, portfolio_list)

        strategic_intelligence = compute_strategic_layer(
            profile_dict,
            portfolio_list,
            score_value,
            financial_features
        )

        # =========================
        # RESULT
        # =========================
        result = {
            "user": user.email,
            "plan": user.plan,
            "strategic_intelligence": strategic_intelligence,
            "score": {
                "score": score_value,
                "details": score_result.get("details", {}),
                "advice": score_result.get("advice", [])
            },
            "level": level,
            "onboarding": onboarding,
            "upgrade": upgrade,
            "features": features,
            "opportunities": opportunities
        }

        set_cache(cache_key, result, ttl=60)
        return result
