# =========================
# IMPORTS
# =========================
from datetime import datetime, date
import hashlib
import json
import random

from core.cache import redis_client


# =========================
# STATIC QUESTS
# =========================
DAILY_QUESTS = [
    {"id": 1, "type": "finance", "task": "Ajouter un revenu", "xp": 20},
    {"id": 2, "type": "portfolio", "task": "Analyser ton portefeuille", "xp": 15},
    {"id": 3, "type": "ai", "task": "Poser une question à l’AI coach", "xp": 25},
    {"id": 4, "type": "optimization", "task": "Réduire une dépense", "xp": 20},
    {"id": 5, "type": "growth", "task": "Identifier une opportunité", "xp": 30},
]


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


def set_cache(key, value, ttl=3600):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# USER SEED ENGINE (STABLE RANDOM)
# =========================
def generate_seed(user_profile: dict, today: str):
    raw = f"{user_profile.get('email','anon')}:{today}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16)


# =========================
# DAILY QUEST ENGINE (STABLE + SAAS READY)
# =========================
def generate_daily_quests(user_profile: dict):

    email = user_profile.get("email", "anon")
    plan = (user_profile.get("plan") or "FREE").upper()

    today = date.today().isoformat()
    cache_key = f"quests:{email}:{today}"

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    # =========================
    # STABLE RANDOM SEED
    # =========================
    seed = generate_seed(user_profile, today)
    rng = random.Random(seed)

    quests = rng.sample(DAILY_QUESTS, 3)

    # =========================
    # PLAN BASED QUESTS
    # =========================
    if plan in ["SILVER", "GOLD", "ELITE", "LIBERTY"]:
        quests.append({
            "id": 100,
            "type": "analysis",
            "task": "Lire analyse IA du jour",
            "xp": 15
        })

    if plan in ["GOLD", "ELITE", "LIBERTY"]:
        quests.append({
            "id": 101,
            "type": "optimization",
            "task": "Optimiser allocation",
            "xp": 25
        })

    if plan in ["ELITE", "LIBERTY"]:
        quests.append({
            "id": 102,
            "type": "strategy",
            "task": "Simuler stratégie avancée",
            "xp": 40
        })

    if plan == "LIBERTY":
        quests.append({
            "id": 999,
            "type": "freedom",
            "task": "Identifier une opportunité liberté financière",
            "xp": 60
        })

    # =========================
    # PAYLOAD FINAL
    # =========================
    result = {
        "date": today,
        "user": email,
        "plan": plan,
        "quests": quests,
        "total_xp": sum(q.get("xp", 0) for q in quests)
    }

    # =========================
    # CACHE STORE (1 DAY)
    # =========================
    set_cache(cache_key, result, ttl=86400)

    return result
