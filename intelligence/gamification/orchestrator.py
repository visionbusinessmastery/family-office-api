# =========================
# IMPORTS
# =========================
from intelligence.gamification.xp_engine import compute_xp
from intelligence.gamification.rewards import compute_reward_bonus
from intelligence.gamification.ai_coach import ai_coach_insight
from intelligence.gamification.notifications import generate_notification


# =========================
# BUILD GAMIFICATION
# =========================
def build_gamification(user, score, plan, streak, action="view_dashboard"):

    # =========================
    # XP CORE
    # =========================
    base_xp = compute_xp(
        action,
        streak=streak,
        liberty_mode=(plan == "LIBERTY")
    )

    reward = compute_reward_bonus(streak, plan)

    total_xp = base_xp + reward.get("bonus_xp", 0)

    # =========================
    # AI COACH
    # =========================
    coach = ai_coach_insight(score, plan, streak)

    # =========================
    # NOTIFICATIONS
    # =========================
    notification = generate_notification(
        {"plan": plan, "streak": streak},
        {"xp_gain": {"final_xp": total_xp}}
    )

    return {
        "xp": total_xp,
        "reward": reward,
        "ai_coach": coach,
        "notification": notification
    }
