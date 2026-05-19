from product.entitlements import normalize_plan, plan_allows


def generate_notification(user_state: dict, gamification: dict):
    plan = normalize_plan(user_state.get("plan"))
    streak = user_state.get("streak", 0)
    xp = 0

    if isinstance(gamification, dict):
        xp_data = gamification.get("xp_gain", {})
        if isinstance(xp_data, dict):
            xp = xp_data.get("final_xp", 0) or 0

    if plan_allows(plan, "LEGACY"):
        return {
            "type": "legacy",
            "priority": "max",
            "message": "Legacy actif: proteger, transmettre et stabiliser devient la priorite.",
        }

    if plan_allows(plan, "LIBERTY"):
        return {
            "type": "liberty",
            "priority": "max",
            "message": "Liberty actif: ton systeme financier gagne en autonomie.",
        }

    if streak >= 14:
        return {
            "type": "elite_streak",
            "priority": "high",
            "message": "Momentum Elite: ton avance se construit dans la regularite.",
        }

    if streak >= 7:
        return {
            "type": "streak",
            "priority": "medium",
            "message": "Streak actif: tu construis un avantage cumulatif.",
        }

    if xp == 0:
        return {
            "type": "neutral",
            "priority": "low",
            "message": "Connecte ton activite pour commencer ta progression.",
        }

    if xp < 10:
        return {
            "type": "info",
            "priority": "low",
            "message": "Petite progression enregistree. Continue avec calme.",
        }

    if xp < 25:
        return {
            "type": "positive",
            "priority": "medium",
            "message": "Bonne dynamique. Ton capital de progression augmente.",
        }

    if xp < 50:
        return {
            "type": "strong_positive",
            "priority": "high",
            "message": "Excellente activite. Tu avances plus vite que la moyenne.",
        }

    return {
        "type": "default",
        "priority": "low",
        "message": "Progression enregistree.",
    }
