from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.upgrade_engine import compute_upgrade_decision


def run_user_intelligence(user_email, profile, portfolio, conn):

    # =========================
    # 1. SCORE
    # =========================
    score_data = compute_family_office_score(profile, portfolio)

    # =========================
    # 2. SEGMENTATION SIMPLE (MVP)
    # =========================
    score = score_data["score"]

    if score >= 85:
        segment = "ELITE_INVESTOR"
    elif score >= 70:
        segment = "ADVANCED"
    elif score >= 50:
        segment = "GROWTH"
    else:
        segment = "BEGINNER"

    # =========================
    # 3. UPGRADE ENGINE
    # =========================
    upgrade = compute_upgrade_decision(
        current_plan=profile.get("plan", "FREE"),
        score=score
    )

    # =========================
    # 4. ACTIONS AUTOMATIQUES
    # =========================
    if upgrade.get("upgrade"):

        conn.execute("""
            UPDATE users
            SET plan = %s
            WHERE email = %s
        """, (upgrade["to"], user_email))

        conn.execute("""
            INSERT INTO upgrade_events (
                user_email, from_plan, to_plan, trigger, score
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            user_email,
            upgrade["from"],
            upgrade["to"],
            upgrade["reason"],
            score
        ))

    # =========================
    # 5. RETURN UNIFIED OUTPUT
    # =========================
    return {
        "score": score_data,
        "segment": segment,
        "upgrade": upgrade
    }
