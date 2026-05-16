# =========================
# REWARD ENGINE (PRODUCTION SAFE)
# =========================

import random


def compute_reward_bonus(streak: int, plan: str, daily_actions: int = 0):

    bonus = 0
    reason = []

    plan = (plan or "FREE").upper()

    # =========================
    # DAILY CAP PROTECTION (ANTI FARM)
    # =========================
    if daily_actions >= 20:
        return {
            "bonus_xp": 0,
            "reasons": ["daily_cap_reached"]
        }

    # =========================
    # STREAK SYSTEM (LINEAR + SAFE)
    # =========================
    if streak >= 3:
        bonus += 5
        reason.append("streak_3")

    if streak >= 7:
        bonus += 10
        reason.append("streak_7")

    if streak >= 14:
        bonus += 20
        reason.append("streak_14")

    # =========================
    # CONTROLLED ENGAGEMENT BOOST (NO PURE RANDOM)
    # =========================
    engagement_score = (streak + daily_actions) % 100

    if engagement_score > 85:
        bonus += 5
        reason.append("high_engagement_boost")

    # =========================
    # PLAN MULTIPLIER (SAFE SCALING)
    # =========================
    if plan == "LIBERTY":
        bonus += 15
        reason.append("liberty_multiplier")

    elif plan == "ELITE":
        bonus += 10
        reason.append("elite_multiplier")

    # =========================
    # HARD CAP (IMPORTANT)
    # =========================
    bonus = min(bonus, 40)

    return {
        "bonus_xp": bonus,
        "reasons": reason
    }
