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
        # 1. USER (CORE)
        # =========================
        user = conn.execute(text("""
            SELECT id, email, plan, profile_completed
            FROM users
            WHERE email = :email
        """), {"email": user_email}).fetchone()

        if not user:
            return {"error": "user not found"}

        # =========================
        # 2. PROFILE DATA (SAFE FIX)
        # =========================
        profile = conn.execute(text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """), {"email": user_email}).fetchone()

        # 🔥 SAFE PROFILE FIX (ANTI-CRASH)
        if not profile:
            profile_dict = {
                "plan": user.plan,
                "savings": 0,
                "investments": 0,
                "risk_profile": "medium"
            }
        else:
            profile_dict = dict(profile._mapping)

        # enrichissement
        profile_dict["email"] = user.email
        profile_dict["plan"] = user.plan

        # =========================
        # 3. PORTFOLIO (SAFE + ADAPTÉ À TA DB)
        # =========================
        try:
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
                    "type": p.category,   # mapping vers "type"
                    "value": float(value) # mapping vers "value"
                })

        except Exception as e:
            print("PORTFOLIO ERROR:", e)
            portfolio_list = []

    # =========================
    # 4. SCORE
    # =========================
    score_result = compute_family_office_score(profile_dict, portfolio_list)
    score = score_result.get("score", 0)

    # =========================
    # 5. LEVEL
    # =========================
    if score >= 80:
        level = "ELITE"
        recommendation = "optimize & scale"
    elif score >= 60:
        level = "GOLD"
        recommendation = "upgrade recommended"
    elif score >= 40:
        level = "SILVER"
        recommendation = "build portfolio"
    else:
        level = "FREE"
        recommendation = "start onboarding"

    # =========================
    # 6. UPGRADE ENGINE
    # =========================
    upgrade = compute_upgrade_decision(
        current_plan=user.plan,
        score=score
    )

    # =========================
    # 7. FEATURES
    # =========================
    features = compute_feature_access(profile_dict, score_result)

    # =========================
    # 8. OPPORTUNITIES
    # =========================
    opportunities = compute_opportunities(profile_dict, portfolio_list)

    # =========================
    # 9. FINAL OUTPUT
    # =========================
    return {
        "user": user.email,
        "plan": user.plan,

        # CORE
        "score": score_result,
        "level": level,
        "recommendation": recommendation,

        # BUSINESS
        "upgrade": upgrade,

        # AI LAYER
        "features": features,
        "opportunities": opportunities
    }
