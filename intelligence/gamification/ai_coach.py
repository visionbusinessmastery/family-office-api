import json

from core.cache import redis_client


def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


COACH_LEVELS = {
    "FREE": {
        "message": "Tu construis tes bases financieres.",
        "recommendation": "Ajoute tes donnees pour debloquer ton potentiel.",
    },
    "SILVER": {
        "message": "Tu es en phase de structuration.",
        "recommendation": "Optimise ton portefeuille.",
    },
    "GOLD": {
        "message": "Tu es en phase de croissance.",
        "recommendation": "Passe sur de l'optimisation avancee.",
    },
    "ELITE": {
        "message": "Tu es en mode avance.",
        "recommendation": "Laisse Ethan surveiller les arbitrages prioritaires.",
    },
    "LIBERTY": {
        "message": "Tu pilotes ton capital avec une logique d'autonomie.",
        "recommendation": "Automatise, protege et scale ton capital avec discipline.",
    },
    "LEGACY": {
        "message": "Le vrai luxe est la stabilite.",
        "recommendation": "Structure la transmission, la gouvernance et la protection familiale.",
    },
}


def ai_coach_insight(score: float, level: str, streak: int = 0, user_id: str = None):
    level = (level or "FREE").upper()
    cache_key = f"ethan:{user_id}:{level}:{int(score)}:{streak}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    base = COACH_LEVELS.get(level, COACH_LEVELS["FREE"])
    message = base["message"]
    recommendation = base["recommendation"]

    if level == "LEGACY":
        if score >= 80:
            message += " Ton patrimoine doit maintenant survivre aux emotions et au temps."
        else:
            message += " Construire est difficile. Preserver l'est encore plus."
    elif score >= 80:
        message += " Performance elevee detectee."
    elif score >= 50:
        message += " Progression stable."
    else:
        message += " Potentiel inexplore."

    if streak >= 7:
        message += " Momentum actif."
    if streak >= 14:
        message += " Discipline patrimoniale solide."
    if streak >= 30:
        message += " Regularite exceptionnelle detectee."

    result = {
        "level": level,
        "score": score,
        "streak": streak,
        "message": message,
        "recommendation": recommendation,
    }

    set_cache(cache_key, result, ttl=300)
    return result
