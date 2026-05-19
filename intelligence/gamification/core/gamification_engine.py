# =========================
# IMPORTS
# =========================
from intelligence.gamification.xp_engine import compute_xp
from intelligence.gamification.rewards import compute_reward_bonus
from intelligence.gamification.ai_coach import ai_coach_insight
from intelligence.gamification.notifications import generate_notification
from product.entitlements import normalize_plan, plan_allows

from core.cache import redis_client
import json


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except:
        pass
    return None


def set_cache(key, value, ttl=120):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# SYNCHRO GAMIFICATION (CORE ENGINE)
# =========================
def sync_gamification(user, score, plan, streak, action="view_dashboard"):

    user_email = user.get("email") if isinstance(user, dict) else str(user)
    plan = normalize_plan(plan)

    # =========================
    # CACHE KEY
    # =========================
    cache_key = f"gamification_core:{user_email}:{action}:{streak}:{plan}:{score}"

    # =========================
    # CACHE HIT
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    # =========================
    # XP ENGINE
    # =========================
    xp = compute_xp(
        action,
        streak=streak,
        liberty_mode=plan_allows(plan, "LIBERTY")
    )

    # =========================
    # REWARD ENGINE
    # =========================
    reward = compute_reward_bonus(streak, plan)

    total_xp = xp + reward.get("bonus_xp", 0)

    # =========================
    # AI COACH ENGINE
    # =========================
    coach = ai_coach_insight(score, plan, streak)

    # =========================
    # NOTIFICATION ENGINE
    # =========================
    notification = generate_notification(
        {
            "plan": plan,
            "streak": streak,
            "score": score,
            "user": user_email
        },
        {
            "xp_gain": {
                "base": xp,
                "bonus": reward.get("bonus_xp", 0),
                "final": total_xp
            }
        }
    )

    result = {
        "xp": total_xp,
        "base_xp": xp,
        "reward": reward,
        "ai_coach": coach,
        "notification": notification
    }

    # =========================
    # CACHE STORE
    # =========================
    set_cache(cache_key, result, ttl=120)

    return result


# =========================
# GAMIFICATION ORCHESTRATOR (WRAPPER LOCAL)
# =========================
def build_gamification(
    user,
    score,
    plan="BASIC",
    streak=0,
    action="view_dashboard"
):
    """
    Wrapper propre pour usage orchestrator global
    """

    return sync_gamification(
        user=user,
        score=score,
        plan=plan,
        streak=streak,
        action=action
    )
