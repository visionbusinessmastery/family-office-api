from intelligence.gamification.xp_engine import compute_xp
from intelligence.gamification.ai_coach import ai_coach_insight
from intelligence.gamification.rewards import compute_reward_bonus
from intelligence.gamification.notifications import generate_notification


def build_gamification(user, score, plan, streak):

    xp = compute_xp(
        "view_dashboard",
        streak=streak,
        liberty_mode=(plan == "LIBERTY")
    )

    coach = ai_coach_insight(score, plan, streak)
    reward = compute_reward_bonus(streak, plan)
    notification = generate_notification(
        {"plan": plan, "streak": streak},
        {"xp_gain": xp}
    )

    return {
        "xp": xp,
        "ai_coach": coach,
        "reward": reward,
        "notification": notification
    }
