# =========================
# GAMIFICATION ORCHESTRATOR (CLEAN SAAS CORE)
# =========================

from intelligence.gamification.xp_engine import compute_xp
from intelligence.gamification.rewards import compute_reward_bonus
from intelligence.gamification.streak_engine import update_streak
from intelligence.gamification.ai_coach import ai_coach_insight
from intelligence.gamification.notifications import generate_notification


# =========================
# MAIN PIPELINE
# =========================
def build_gamification(user, score, plan, streak, action="view_dashboard"):

    # 1. XP ENGINE
    base_xp = compute_xp(
        action,
        streak=streak,
        liberty_mode=(plan == "LIBERTY")
    )

    # 2. REWARDS ENGINE
    reward = compute_reward_bonus(streak, plan)

    total_xp = base_xp + reward.get("bonus_xp", 0)

    # 3. AI COACH
    coach = ai_coach_insight(score, plan, streak)

    # 4. NOTIFICATIONS
    notification = generate_notification(
        {"plan": plan, "streak": streak},
        {"xp_gain": {"final_xp": total_xp}}
    )

    # 5. OUTPUT CLEAN
    return {
        "xp": total_xp,
        "reward": reward,
        "ai_coach": coach,
        "notification": notification
    }
