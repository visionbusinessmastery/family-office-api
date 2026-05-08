# =========================
# AI COACH SYSTEM V1
# =========================

def ai_coach_insight(score: float, level: str, streak: int = 0):

    level = (level or "FREE").upper()

    message = ""
    recommendation = ""

    if level == "FREE":
        message = "Tu construis tes bases financières."
        recommendation = "Ajoute tes données pour débloquer ton potentiel."

    elif level == "SILVER":
        message = "Tu es en phase de structuration."
        recommendation = "Optimise ton portefeuille."

    elif level == "GOLD":
        message = "Tu es en phase de croissance."
        recommendation = "Passe sur de l’optimisation avancée."

    elif level == "ELITE":
        message = "Tu es en mode avancé."
        recommendation = "Active les prédictions IA."

    elif level == "LIBERTY":
        message = "Tu es en mode Wealth OS."
        recommendation = "Automatise et scale ton capital."

    # STREAK BOOST
    if streak >= 7:
        message += " 🔥 Momentum actif."

    if streak >= 14:
        message += " ⚡ Croissance exponentielle."

    return {
        "level": level,
        "score": score,
        "streak": streak,
        "message": message,
        "recommendation": recommendation
    }
