from sqlalchemy import text
from database import engine

from intelligence.analyzers.family_office_score import compute_family_office_score


# =========================
# MAIN ENGINE
# =========================
def compute_user_intelligence(user_email: str):

    with engine.begin() as conn:

        # =========================
        # 1. USER PROFILE
        # =========================
        user = conn.execute(text("""
            SELECT email, plan, profile_completed
            FROM users
            WHERE email = :email
        """), {"email": user_email}).fetchone()

        if not user:
            return {"error": "user not found"}

        # =========================
        # 2. USER PROFILE DATA
        # =========================
        profile = conn.execute(text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """), {"email": user_email}).fetchone()

        profile_dict = dict(profile._mapping) if profile else {}

        # =========================
        # 3. PORTFOLIO DATA
        # =========================
        portfolio = conn.execute(text("""
            SELECT asset_name, type, value
            FROM portfolio
            WHERE user_email = :email
        """), {"email": user_email}).fetchall()

        portfolio_list = [dict(p._mapping) for p in portfolio]

    # =========================
    # 4. FAMILY OFFICE SCORE
    # =========================
    score_result = compute_family_office_score(profile_dict, portfolio_list)

    # =========================
    # 5. USER MATURITY LEVEL
    # =========================
    score = score_result["score"]

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
    # 6. BUSINESS LOGIC
    # =========================
    upgrade_target = None

    if level == "FREE":
        upgrade_target = "SILVER"
    elif level == "SILVER":
        upgrade_target = "GOLD"
    elif level == "GOLD":
        upgrade_target = "ELITE"

    # =========================
    # 7. FINAL OUTPUT
    # =========================
    return {
        "user": user_email,
        "plan": user.plan,
        "score": score_result,
        "level": level,
        "recommendation": recommendation,
        "upgrade_target": upgrade_target
    }
