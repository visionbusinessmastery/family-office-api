# =========================
# AI COACH SYSTEM V2 (SAAS READY)
# =========================

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
# COACH RULES ENGINE (EXTENSIBLE)
# =========================
COACH_LEVELS = {
    "FREE": {
        "message": "Tu construis tes bases financières.",
        "recommendation": "Ajoute tes données pour débloquer ton potentiel."
    },
    "SILVER": {
        "message": "Tu es en phase de structuration.",
        "recommendation": "Optimise ton portefeuille."
    },
    "GOLD": {
        "message": "Tu es en phase de croissance.",
        "recommendation": "Passe sur de l’optimisation avancée."
    },
    "ELITE": {
        "message": "Tu es en mode avancé.",
        "recommendation": "Active les prédictions IA."
    },
    "LIBERTY": {
        "message": "Tu es en mode Wealth OS.",
        "recommendation": "Automatise et scale ton capital."
    }
}


# =========================
# AI COACH SYSTEM V2
# =========================
def ai_coach_insight(score: float, level: str, streak: int = 0, user_id: str = None):

    level = (level or "FREE").upper()

    cache_key = f"ai_coach:{user_id}:{level}:{int(score)}:{streak}"

    # =========================
    # CACHE HIT
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    # =========================
    # BASE COACH DATA
    # =========================
    base = COACH_LEVELS.get(level, COACH_LEVELS["FREE"])

    message = base["message"]
    recommendation = base["recommendation"]

    # =========================
    # SCORE ENHANCEMENT (SMART LAYER)
    # =========================
    if score >= 80:
        message += " 🚀 Performance élevée détectée."

    elif score >= 50:
        message += " 📈 Progression stable."

    else:
        message += " 📉 Potentiel inexploité."

    # =========================
    # STREAK BOOST SYSTEM
    # =========================
    if streak >= 7:
        message += " 🔥 Momentum actif."

    if streak >= 14:
        message += " ⚡ Croissance exponentielle."

    if streak >= 30:
        message += " 🧠 Discipline exceptionnelle détectée."

    result = {
        "level": level,
        "score": score,
        "streak": streak,
        "message": message,
        "recommendation": recommendation
    }

    # =========================
    # CACHE STORE
    # =========================
    set_cache(cache_key, result, ttl=300)

    return result
