# =========================
# IMPORTS
# =========================
from sqlalchemy import text
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


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# BADGE RULES ENGINE (EXTENSIBLE)
# =========================
BADGE_RULES = [
    (1, "Premier revenu"),
    (10, "Analyste"),
    (50, "Investisseur actif"),
    (100, "Elite financier"),
    (500, "Whale Investor"),
]


# =========================
# UNLOCK BADGES (SAFE + IDENTITY + CACHE)
# =========================
def unlock_badges(conn, user_id: int):

    cache_key = f"badges:{user_id}"

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    # =========================
    # GET TOTAL (SAFE)
    # =========================
    rows = conn.execute(
        text("""
            SELECT COUNT(*) as total
            FROM finance_items
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).fetchone()

    total = rows.total if rows and rows.total is not None else 0

    # =========================
    # GET CURRENT BADGES
    # =========================
    existing = conn.execute(
        text("""
            SELECT badges
            FROM user_gamification
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).fetchone()

    existing_badges = set()
    if existing and existing.badges:
        existing_badges = set(existing.badges.split(","))

    # =========================
    # BUILD NEW BADGES (NO OVERWRITE LOSS)
    # =========================
    new_badges = set(existing_badges)

    for threshold, badge in BADGE_RULES:
        if total >= threshold:
            new_badges.add(badge)

    final_badges = sorted(list(new_badges))

    # =========================
    # UPDATE ONLY IF CHANGED
    # =========================
    if final_badges != list(existing_badges):

        conn.execute(
            text("""
                UPDATE user_gamification
                SET badges = :badges
                WHERE user_id = :user_id
            """),
            {
                "badges": ",".join(final_badges),
                "user_id": user_id
            }
        )

    result = {
        "user_id": user_id,
        "total_actions": total,
        "badges": final_badges
    }

    # =========================
    # CACHE STORE
    # =========================
    set_cache(cache_key, result, ttl=300)

    return result
