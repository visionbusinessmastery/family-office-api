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
# SAFE GETTER
# =========================
def safe_get(obj, key, default=0):
    try:
        return obj.get(key, default) if isinstance(obj, dict) else default
    except Exception:
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
# MAIN ENGINE (CACHE OPTIMIZED SAFE)
# =========================
def compute_user_intelligence(user_email: str):

    cache_key = f"intel:{user_email}"

    # =========================
    # CACHE CHECK (SAFE)
    # =========================
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass  # NEVER break flow

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
        # ONBOARDING REQUIRED
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

            # cache safe
            if redis_client:
                try:
                    redis_client.setex(cache_key, 30, json.dumps(result))
                except:
                    pass

            return result

        # =========================
        # PROFILE
        # =========================
        profile = conn.execute(text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """), {"email": user_email}).fetchone()

        profile_dict = dict(profile._mapping) if profile else {}

        # =========================
        # ONBOARDING NORMALIZED
        # =========================
        onboarding = {
            "monthly_income": float(user.revenus_mensuels or 0),
            "monthly_expenses": float(user.charges_mensuelles or 0),
            "epargne": float(profile_dict.get("savings") or 0),
            "dettes": float(profile_dict.get("debts") or 0),
        }

        # =========================
        # PROFILE CLEAN
        # =========================
        profile_dict = {
            "epargne": onboarding["epargne"],
            "investments": float(profile_dict.get("investments") or 0),
            "risk_profile": (profile_dict.get("risk_profile") or "medium").lower(),
            "monthly_income": onboarding["monthly_income"],
            "debt": onboarding["dettes"],
            "email": user.email,
            "plan": user.plan,
        }

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

        financial_features = {}
        totals = financial.get("totals", {}) if isinstance(financial, dict) else {}

        if totals:
            financial_features = {
                "cashflow_score": safe_get(totals, "net_cashflow", 0),
                "debt_risk_score": safe_get(totals, "total_debt", 0),
                "savings_velocity_score": safe_get(totals, "total_savings", 0),
                "income_stability_score": len(financial.get("income_sources", [])) * 10,
                "raw": totals
            }

        # =========================
        # SCORE ENGINE
        # =========================
        score_result = compute_family_office_score(
            profile_dict,
            portfolio_list,
            financial_features
        ) or {}

        score_value = safe_get(score_result, "score", 0)

        if isinstance(score_value, dict):
            score_value = safe_get(score_value, "score", 0)

        score_value = int(score_value or 0)

        # =========================
        # LEVEL
        # =========================
        level = compute_level(score_value, user.plan)

        # =========================
        # ENGINE CALLS
        # =========================
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

        # =========================
        # CACHE STORE SAFE
        # =========================
        if redis_client:
            try:
                redis_client.setex(cache_key, 60, json.dumps(result))
            except:
                pass

        return result
