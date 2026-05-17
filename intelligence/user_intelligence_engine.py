# =========================
# USER INTELLIGENCE ENGINE
# =========================

# =========================
# IMPORTS
# =========================
from sqlalchemy import text

from core.cache import redis_client
from database import engine
from intelligence.core.upgrade_engine import compute_upgrade_decision
from intelligence.scoring.family_office_score import (
    compute_family_office_score,
    safe_get,
)
from intelligence.service import get_user_financial_overview
from intelligence.strategic.feature_engine import compute_feature_access
from intelligence.strategic.opportunity_engine import compute_opportunities
from intelligence.strategic.strategic_layer import compute_strategic_layer


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                import json

                return json.loads(data)
    except Exception:
        pass

    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            import json

            redis_client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


# =========================
# LEVEL ENGINE
# =========================
def compute_level(score: int, plan: str = "FREE"):
    if (plan or "").upper() == "LIBERTY":
        return "LIBERTY"
    if score >= 85:
        return "ELITE"
    if score >= 70:
        return "ADVANCED"
    if score >= 50:
        return "INTERMEDIATE"
    return "BEGINNER"


# =========================
# FINANCE HELPERS
# =========================
def build_finance_payload(conn, user_id: int, onboarding: dict):
    finance = {
        "revenus": [],
        "charges": [],
        "epargne": [],
        "dettes": [],
    }

    rows = conn.execute(text("""
        SELECT type, name, amount
        FROM finance_items
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchall()

    for row in rows:
        item_type = row.type
        if item_type not in finance:
            continue

        finance[item_type].append({
            "name": row.name,
            "label": row.name,
            "amount": float(row.amount or 0),
        })

    if onboarding.get("monthly_income", 0) > 0:
        finance["revenus"].append({
            "label": "Onboarding Income",
            "amount": onboarding["monthly_income"],
        })

    if onboarding.get("monthly_expenses", 0) > 0:
        finance["charges"].append({
            "label": "Onboarding Charges",
            "amount": onboarding["monthly_expenses"],
        })

    if onboarding.get("savings", 0) > 0:
        finance["epargne"].append({
            "label": "Profile Savings",
            "amount": onboarding["savings"],
        })

    if onboarding.get("debts", 0) > 0:
        finance["dettes"].append({
            "label": "Profile Debts",
            "amount": onboarding["debts"],
        })

    return finance


def sum_amount(items):
    return sum(float(item.get("amount") or 0) for item in items)


# =========================
# MAIN ENGINE
# =========================
def compute_user_intelligence(user_email: str):

    cache_key = f"intel:{user_email}"
    context_cache_key = f"context:{user_email}"

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
        # ONBOARDING REQUIRED STATE
        # =========================
        if not user.profile_completed:

            onboarding = {
                "monthly_income": float(user.revenus_mensuels or 0),
                "monthly_expenses": float(user.charges_mensuelles or 0),
                "savings": 0,
                "debts": 0,
            }

            result = {
                "state": "ONBOARDING_REQUIRED",
                "user": user.email,
                "plan": user.plan,
                "global_score": 0,
                "level": "ONBOARDING",
                "onboarding": onboarding,
                "family_office_score": {
                    "score": 0,
                    "level": "ONBOARDING",
                    "details": {},
                    "advice": [],
                },
                "modules": {},
               "advice": [],
            }

            set_cache(cache_key, result, ttl=30)
            return result

        # =========================
        # CONTEXT CACHE
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

        # =========================
        # FINANCIAL OVERVIEW
        # =========================
        finance_payload = build_finance_payload(conn, user.id, onboarding)
        financial_overview = get_user_financial_overview(user.id) or {}
        totals = financial_overview.get("totals", {}) if isinstance(financial_overview, dict) else {}

        total_income = sum_amount(finance_payload["revenus"])
        total_expenses = sum_amount(finance_payload["charges"])
        total_debt = sum_amount(finance_payload["dettes"])
        total_savings = sum_amount(finance_payload["epargne"])

        financial_features = {
            "cashflow_score": total_income - total_expenses,
            "monthly_income": onboarding["monthly_income"],
            "monthly_expenses": onboarding["monthly_expenses"],
            "debt_risk_score": total_debt or safe_get(totals, "total_debt", 0),
            "savings_velocity_score": total_savings or safe_get(totals, "total_savings", 0),
            "income_stability_score": len(finance_payload["revenus"]) * 10,
            "raw": {
                **totals,
                "finance_items_income": total_income,
                "finance_items_expenses": total_expenses,
                "finance_items_debt": total_debt,
                "finance_items_savings": total_savings,
            }
        }

        # =========================
        # SCORE ENGINE
        # =========================
        score_result = compute_family_office_score(
            profile_dict,
            portfolio_list,
            finance_payload
        ) or {}

        score_value = int(safe_get(score_result, "score", 0))

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
        # FINAL RESULT
        # =========================
        result = {
            "user": user.email,
            "plan": user.plan,

            "global_score": score_value,
            "level": level,

             "onboarding": onboarding,
            "finance": finance_payload,
            "financial_overview": financial_overview,
            "financial_features": financial_features,
            "family_office_score": score_result,
            "score": score_result,
            "strategic_intelligence": strategic_intelligence,

            "modules": score_result.get("details", {}),

            "advice": score_result.get("advice", []),

            "upgrade": upgrade,
            "features": features,
            "opportunities": opportunities,
        }

        set_cache(cache_key, result, ttl=60)
        return result
