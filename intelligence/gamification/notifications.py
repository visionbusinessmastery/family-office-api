# =========================
# NOTIFICATION ENGINE (PRODUCTION READY)
# =========================

def generate_notification(user_state: dict, gamification: dict):

    plan = (user_state.get("plan") or "FREE").upper()
    streak = user_state.get("streak", 0)

    xp = 0

    # =========================
    # SAFE XP EXTRACTION
    # =========================
    if isinstance(gamification, dict):
        xp_data = gamification.get("xp_gain", {})
        if isinstance(xp_data, dict):
            xp = xp_data.get("final_xp", 0) or 0

    # =========================
    # 1. LIBERTY OVERRIDE (HIGHEST PRIORITY)
    # =========================
    if plan == "LIBERTY":
        return {
            "type": "liberty",
            "priority": "max",
            "message": "🏆 LIBERTY MODE actif — système financier autonome en croissance."
        }

    # =========================
    # 2. STREAK OVERRIDE (STRATEGIC PRIORITY)
    # =========================
    if streak >= 14:
        return {
            "type": "elite_streak",
            "priority": "high",
            "message": "💎 Momentum Elite ! Effet boule de neige actif."
        }

    if streak >= 7:
        return {
            "type": "streak",
            "priority": "medium",
            "message": "⚡ Streak actif ! Tu construis un avantage cumulatif."
        }

    # =========================
    # 3. XP PROGRESSION ENGINE
    # =========================
    if xp == 0:
        return {
            "type": "neutral",
            "priority": "low",
            "message": "Connecte ton activité pour commencer ta progression."
        }

    if xp < 10:
        return {
            "type": "info",
            "priority": "low",
            "message": "Petite progression 👌 continue pour accélérer ton score."
        }

    if xp < 25:
        return {
            "type": "positive",
            "priority": "medium",
            "message": "🔥 Bonne dynamique ! Ton capital de progression augmente."
        }

    if xp < 50:
        return {
            "type": "strong_positive",
            "priority": "high",
            "message": "🚀 Excellente activité ! Tu avances plus vite que la moyenne."
        }

    # =========================
    # FALLBACK
    # =========================
    return {
        "type": "default",
        "priority": "low",
        "message": "Progression enregistrée."
    }
