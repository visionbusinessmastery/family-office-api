from datetime import date
import hashlib
import json
import random

from core.cache import redis_client
from product.entitlements import normalize_plan, plan_allows


DAILY_QUESTS = [
    {"id": 1, "type": "finance", "task": "Ajouter un revenu", "xp": 20},
    {"id": 2, "type": "portfolio", "task": "Analyser ton portefeuille", "xp": 15},
    {"id": 3, "type": "advisor", "task": "Ouvrir le copilote", "xp": 25},
    {"id": 4, "type": "optimization", "task": "Reduire une depense", "xp": 20},
    {"id": 5, "type": "growth", "task": "Identifier une opportunite", "xp": 30},
]


def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    return None


def set_cache(key, value, ttl=3600):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def generate_seed(user_profile: dict, today: str):
    raw = f"{user_profile.get('email', 'anon')}:{today}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16)


def generate_daily_quests(user_profile: dict):
    email = user_profile.get("email", "anon")
    plan = normalize_plan(user_profile.get("plan"))

    today = date.today().isoformat()
    cache_key = f"quests:{email}:{plan}:{today}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    seed = generate_seed(user_profile, today)
    rng = random.Random(seed)
    quests = rng.sample(DAILY_QUESTS, 3)

    if plan_allows(plan, "GOLD"):
        quests.append({
            "id": 100,
            "type": "analysis",
            "task": "Lire les signaux du jour",
            "xp": 15,
        })

    if plan_allows(plan, "GOLD"):
        quests.append({
            "id": 101,
            "type": "optimization",
            "task": "Optimiser allocation",
            "xp": 25,
        })

    if plan_allows(plan, "ELITE"):
        quests.append({
            "id": 102,
            "type": "strategy",
            "task": "Simuler strategie avancee",
            "xp": 40,
        })

    if plan_allows(plan, "LIBERTY") and not plan_allows(plan, "LEGACY"):
        quests.append({
            "id": 999,
            "type": "freedom",
            "task": "Identifier une opportunite liberte financiere",
            "xp": 60,
        })

    if plan_allows(plan, "LEGACY"):
        quests.append({
            "id": 1000,
            "type": "legacy",
            "task": "Verifier un point de transmission ou de protection familiale",
            "xp": 45,
        })

    result = {
        "date": today,
        "user": email,
        "plan": plan,
        "quests": quests,
        "total_xp": sum(q.get("xp", 0) for q in quests),
    }

    set_cache(cache_key, result, ttl=86400)
    return result
