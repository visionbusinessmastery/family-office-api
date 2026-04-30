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
        # 3. PORTFOLIO (FIXED)
        # =========================
        portfolio = conn.execute(text("""
            SELECT asset_name, category, quantity, purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": user.id}).fetchall()

        portfolio_list = []

        for p in portfolio:
            value = (p.quantity or 0) * (p.purchase_price or 0)

            portfolio_list.append({
                "asset_name": p.asset_name,
                "type": (p.category or "").lower(),  # 🔥 CRITIQUE pour le scoring
                "value": float(value)
            })

        # 🔥 DEBUG (ultra important)
        print("🔥 PORTFOLIO DEBUG:", portfolio_list)

    # =========================
    # 4. SCORE
    # =========================
    score_result = compute_family_office_score(profile_dict, portfolio_list)
    score = score_result.get("score", 0)

    print("🔥 SCORE DEBUG:", score_result)

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
        "score": score_result,
        "level": level,
        "upgrade": upgrade,
        "features": features,
        "opportunities": opportunities
    }
