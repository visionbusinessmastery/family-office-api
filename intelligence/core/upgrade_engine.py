# =========================
# IMPORTS (SAFE EXTENSION)
# =========================
from sqlalchemy import text

# =========================
# PLAN HIERARCHY
# =========================
PLAN_HIERARCHY = {
    "FREE": 0,
    "SILVER": 1,
    "GOLD": 2,
    "ELITE": 3,
    "LIBERTY": 4
}

# =========================
# PLAN FROM SCORE (XP SYSTEM)
# =========================
def get_plan_from_score(score: int):

    # 🔥 LIBERTY MODE (END GAME)
    if score >= 15000:
        return "LIBERTY"

    # ELITE
    elif score >= 7000:
        return "ELITE"

    # GOLD
    elif score >= 3000:
        return "GOLD"

    # SILVER
    elif score >= 1000:
        return "SILVER"

    # FREE
    return "FREE"


# =========================
# UPGRADE DECISION ENGINE (XP-BASED)
# =========================
def compute_upgrade_decision(current_plan: str, score: int):

    recommended_plan = get_plan_from_score(score)

    current_level = PLAN_HIERARCHY.get(
        (current_plan or "FREE").upper(), 0
    )

    recommended_level = PLAN_HIERARCHY.get(
        recommended_plan, 0
    )

    upgrade = recommended_level > current_level

    return {
        "upgrade": upgrade,
        "from": (current_plan or "FREE").upper(),
        "to": recommended_plan,
        "recommended_plan": recommended_plan,
        "reason": "xp_threshold_reached" if upgrade else None
    }


# =========================
# MAIN PIPELINE (SAFE VERSION)
# =========================
def process_user_intelligence(user_email, profile, portfolio, conn):

    try:

        from intelligence.analyzers.family_office_score import compute_family_office_score

        # =========================
        # SAFE INPUTS
        # =========================
        profile = profile or {}
        portfolio = portfolio or []

        # =========================
        # SCORE COMPUTATION (XP CORE)
        # =========================
        score_data = compute_family_office_score(profile, portfolio)

        score_value = (
            score_data.get("score", 0)
            if isinstance(score_data, dict)
            else 0
        )

        # =========================
        # UPGRADE DECISION
        # =========================
        upgrade = compute_upgrade_decision(
            current_plan=profile.get("plan", "FREE"),
            score=score_value
        )

        # =========================
        # DB UPDATE SAFE (PLAN EVOLUTION)
        # =========================
        if upgrade.get("upgrade"):

            conn.execute(text("""
                UPDATE users
                SET plan = :new_plan
                WHERE email = :email
            """), {
                "new_plan": upgrade["to"],
                "email": user_email
            })

            conn.execute(text("""
                INSERT INTO upgrade_events (
                    user_email,
                    from_plan,
                    to_plan,
                    trigger,
                    score
                )
                VALUES (
                    :email,
                    :from_plan,
                    :to_plan,
                    :trigger,
                    :score
                )
            """), {
                "email": user_email,
                "from_plan": upgrade["from"],
                "to_plan": upgrade["to"],
                "trigger": upgrade["reason"],
                "score": score_value
            })

        # =========================
        # RESPONSE
        # =========================
        return {
            "score": score_data,
            "upgrade": upgrade
        }

    except Exception as e:

        return {
            "error": str(e),
            "score": {
                "score": 0,
                "details": {},
                "advice": []
            },
            "upgrade": {
                "upgrade": False,
                "from": "FREE",
                "to": "FREE",
                "recommended_plan": "FREE",
                "reason": "error"
            }
        }


# =========================
# COMPAT LAYER (SAFE)
# =========================
evaluate_upgrade = compute_upgrade_decision
