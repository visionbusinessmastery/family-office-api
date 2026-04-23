from sqlalchemy import text


# =========================
# PLAN FROM SCORE
# =========================
def get_plan_from_score(score: int):

    if score >= 85:
        return "ELITE"
    elif score >= 70:
        return "GOLD"
    elif score >= 50:
        return "SILVER"
    else:
        return "FREE"


# =========================
# UPGRADE DECISION ENGINE
# =========================
def compute_upgrade_decision(current_plan: str, score: int):

    recommended_plan = get_plan_from_score(score)

    hierarchy = {
        "FREE": 0,
        "SILVER": 1,
        "GOLD": 2,
        "ELITE": 3
    }

    current_level = hierarchy.get(current_plan or "FREE", 0)
    recommended_level = hierarchy.get(recommended_plan, 0)

    if recommended_level > current_level:
        return {
            "upgrade": True,
            "from": current_plan,
            "to": recommended_plan,
            "recommended_plan": recommended_plan,
            "reason": "score_threshold_reached"
        }

    return {
        "upgrade": False,
        "from": current_plan,
        "to": current_plan,
        "recommended_plan": recommended_plan,
        "reason": None
    }


# =========================
# MAIN PIPELINE (OPTIONNEL BACKEND AUTO APPLY)
# =========================
def process_user_intelligence(user_email, profile, portfolio, conn):

    from intelligence.analyzers.family_office_score import compute_family_office_score

    score_data = compute_family_office_score(profile, portfolio)

    upgrade = compute_upgrade_decision(
        current_plan=profile.get("plan", "FREE"),
        score=score_data["score"]
    )

    # =========================
    # AUTO UPGRADE DB
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
            "score": score_data["score"]
        })

    return {
        "score": score_data,
        "upgrade": upgrade
    }


# =========================
# COMPAT LAYER (IMPORTANT)
# =========================
evaluate_upgrade = compute_upgrade_decision
