from datetime import datetime
import random

DAILY_QUESTS = [
    {"id": 1, "type": "finance", "task": "Ajouter un revenu", "xp": 20},
    {"id": 2, "type": "portfolio", "task": "Analyser ton portefeuille", "xp": 15},
    {"id": 3, "type": "ai", "task": "Poser une question à l’AI coach", "xp": 25},
    {"id": 4, "type": "optimization", "task": "Réduire une dépense", "xp": 20},
    {"id": 5, "type": "growth", "task": "Identifier une opportunité", "xp": 30}
]


def generate_daily_quests(user_profile: dict):

    plan = (user_profile.get("plan") or "FREE").upper()

    quests = random.sample(DAILY_QUESTS, 3)

    if plan in ["SILVER", "GOLD", "ELITE", "LIBERTY"]:
        quests.append({"id": 100, "task": "Lire analyse IA du jour", "xp": 15})

    if plan in ["GOLD", "ELITE", "LIBERTY"]:
        quests.append({"id": 101, "task": "Optimiser allocation", "xp": 25})

    if plan in ["ELITE", "LIBERTY"]:
        quests.append({"id": 102, "task": "Simuler stratégie avancée", "xp": 40})

    if plan == "LIBERTY":
        quests.append({"id": 999, "task": "Identifier une opportunité liberté financière", "xp": 60})

    return {
        "date": datetime.utcnow().isoformat(),
        "quests": quests,
        "total_xp": sum(q["xp"] for q in quests)
    }
