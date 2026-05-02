# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine

from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.analyzers.financial_overview import get_user_financial_overview

from intelligence.upgrade_engine import compute_upgrade_decision
from intelligence.feature_engine import compute_feature_access
from intelligence.opportunity_engine import compute_opportunities


# =========================
# PUBLIC API
# =========================
def get_user_intelligence(user_email: str):
    return compute_user_intelligence(user_email)


# =========================
# MAIN ENGINE
# =========================
def compute_user_intelligence(user_email: str):

    with engine.begin() as conn:

        # =========================
        # 1. USER
        # =========================
        user = conn.execute(text("""
            SELECT id, email, plan, profile_completed
            FROM users
            WHERE email = :email
        """), {"email": user_email}).fetchone()

        if not user:
            return {"error": "user not found"}

        # =========================
        # ONBOARDING CHECK
        # =========================
        if not user.profile_completed:
            return {
                "state": "ONBOARDING_REQUIRED",
                "score": {"score": 0},
                "level": "ONBOARDING",
                "features": [],
                "opportunities": [],
                "upgrade": None
            }

        # =========================
        # PROFILE
        # =========================
        profile = conn.execute(text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """), {"email": user_email}).fetchone()

        profile_dict = dict(profile._mapping) if profile else {
            "plan": user.plan,
            "savings": 0,
            "investments": 0,
            "risk_profile": "medium"
        }

        profile_dict["email"] = user.email
        profile_dict["plan"] = user.plan

        # =========================
        # PORTFOLIO
        # =========================
        portfolio = conn.execute(text("""
            SELECT asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": user.id}).fetchall()

        portfolio_list = []

        for p in portfolio:
            qty = float(p.quantity or 0)
            price = float(p.purchase_price or 0)

            portfolio_list.append({
                "asset_name": p.asset_name,
                "type": (p.category or "").lower(),
                "value": qty * price
            })

        # =========================
        # FINANCIAL DATA (NEW LAYER)
        # =========================
        financial = get_user_financial_overview(user.id)

        income = financial["totals"]["monthly_income"]
        debt_payment = financial["totals"]["monthly_debt_payment"]
        savings = financial["totals"]["total_savings"]
        debt = financial["totals"]["total_debt"]
        cashflow = financial["totals"]["net_cashflow"]

        cashflow_score = max(min((cashflow / (income + 1)) * 100, 100), -100)
        debt_risk_score = min((debt / (savings + 1)) * 100, 100)
        savings_velocity = (savings / (income + 1)) * 100
        income_stability_score = min(len(financial.get("income_sources", [])) * 25, 100)

        financial_features = {
            "cashflow_score": round(cashflow_score, 2),
            "debt_risk_score": round(debt_risk_score, 2),
            "savings_velocity_score": round(savings_velocity, 2),
            "income_stability_score": round(income_stability_score, 2),
            "raw": financial["totals"]
        }

    # =========================
    # SCORE ENGINE (UPDATED)
    # =========================
    score_result = compute_family_office_score(
        profile_dict,
        portfolio_list,
        financial_features
    )

    score = score_result.get("score", 0)

    # =========================
    # LEVEL
    # =========================
    if score >= 80:
        level = "ELITE"
    elif score >= 60:
        level = "GOLD"
    elif score >= 40:
        level = "SILVER"
    else:
        level = "FREE"

    # =========================
    # ENGINE LAYER
    # =========================
    upgrade = compute_upgrade_decision(user.plan, score)
    features = compute_feature_access(profile_dict, score_result)
    opportunities = compute_opportunities(profile_dict, portfolio_list)

    return {
        "user": user.email,
        "plan": user.plan,
        "score": {
            "score": score,
            "details": score_result.get("details", {}),
            "advice": score_result.get("advice", []),
            "financial": financial_features
        },
        "level": level,
        "upgrade": upgrade,
        "features": features,
        "opportunities": opportunities
    }
