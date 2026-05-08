# =========================
# REWARD ENGINE (SAFE EXTENSION)
# =========================

import random


def compute_reward_bonus(streak: int, plan: str):

    bonus = 0
    reason = []

    # =========================
    # STREAK BONUSES
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
    # RANDOM ENGAGEMENT BOOST
    # =========================
    lucky = random.randint(1, 100)

    if lucky > 90:
        bonus += 15
        reason.append("lucky_boost")

    # =========================
    # LIBERTY BONUS
    # =========================
    if plan == "LIBERTY":
        bonus += 25
        reason.append("liberty_multiplier")

    return {
        "bonus_xp": bonus,
        "reasons": reason
    }
