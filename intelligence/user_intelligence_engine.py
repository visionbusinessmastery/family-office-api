# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine

from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.upgrade_engine import compute_upgrade_decision
from intelligence.feature_engine import compute_feature_access
from intelligence.opportunity_engine import compute_opportunities


# =========================
# PUBLIC CORE API (SINGLE SOURCE)
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
        # 🛡️ STATE RECOVERY CHECK
        # =========================
        if not user.profile_completed:
            return {
                "state": "ONBOARDING_REQUIRED",
                "score": {
                    "score": 0,
                    "status": "incomplete_profile"
                },
                "level": "ONBOARDING",
                "features": [],
                "opportunities": [],
                "upgrade": None
            }

        # =========================
        # 2. PROFILE
        # =========================
        profile = conn.execute(text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """), {"email": user_email}).fetchone()

        if not profile:
            profile_dict = {
                "plan": user.plan,
                "savings": 0,
                "investments": 0,
                "risk_profile": "medium"
            }
        else:
            profile_dict = dict(profile._mapping)

        profile_dict["email"] = user.email
        profile_dict["plan"] = user.plan

        # =========================
        # 3. PORTFOLIO (FIXED & SAFE)
        # =========================
        portfolio = conn.execute(text("""
            SELECT asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": user.id}).fetchall()

        portfolio_list = []

        for p in portfolio:

            # 🔥 SAFE VALUE CALC (anti-bug)
            qty = float(p.quantity or 0)
            price = float(p.purchase_price or 0)

            value = qty * price

            portfolio_list.append({
                "asset_name": p.asset_name,
                "type": (p.category or "").lower(),
                "value": float(value)
            })

        # 🔥 DEBUG PORTFOLIO
        print("🔥 PORTFOLIO DEBUG:", portfolio_list)

    # =========================
    # 4. SCORE
    # =========================
    score_result = compute_family_office_score(profile_dict, portfolio_list)

    # 🔥 SAFE SCORE EXTRACTION (IMPORTANT FIX)
    if isinstance(score_result, dict) and "score" in score_result:

        # CAS 1: {"score": 62}
        if isinstance(score_result["score"], (int, float)):
            score = score_result["score"]

        # CAS 2: {"score": {"score": 62}}
        elif isinstance(score_result["score"], dict):
            score = score_result["score"].get("score", 0)

        else:
            score = 0
    else:
        score = 0

    print("🔥 SCORE DEBUG:", score_result)
    print("🔥 FINAL SCORE:", score)

    # =========================
    # 5. LEVEL
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
    # 6. ENGINE
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
            "advice": score_result.get("advice", [])
        },
        "level": level,
        "upgrade": upgrade,
        "features": features,
        "opportunities": opportunities
    }


# =========================
# PUBLIC ALIAS (COMPAT ADVISOR)
# =========================
def get_user_intelligence(user_email: str):
    return compute_user_intelligence(user_email)
