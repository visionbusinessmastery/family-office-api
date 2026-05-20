# =========================
# IMPORTS (SAFE EXTENSION)
# =========================
from product.tiers import normalize_plan, plan_rank

# =========================
# PLAN FROM SCORE (XP SYSTEM)
# =========================
def get_plan_from_score(score: int):

    # 🔥 LIBERTY MODE (END GAME)
    if score >= 22000:
        return "LEGACY"

    if score >= 15000:
        return "LIBERTY"

    # ELITE
    elif score >= 7000:
        return "ELITE"

    # GOLD
    elif score >= 3000:
        return "GOLD"

    # SILVER
    return "FREE"


# =========================
# UPGRADE DECISION ENGINE (XP-BASED)
# =========================
def compute_upgrade_decision(current_plan: str, score: int):

    recommended_plan = get_plan_from_score(score)

    normalized_current_plan = normalize_plan(current_plan)
    current_level = plan_rank(normalized_current_plan)
    recommended_level = plan_rank(recommended_plan)

    upgrade = recommended_level > current_level

    return {
        "upgrade": upgrade,
        "from": normalized_current_plan,
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

        # Plans payants et features visibles restent deterministes:
        # cette couche recommande, Stripe/billing synchronise le vrai user.plan.

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
