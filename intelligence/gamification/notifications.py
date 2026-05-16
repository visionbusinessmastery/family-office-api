# =========================
# NOTIFICATION ENGINE (SAFE ADD-ON)
# =========================

def generate_notification(user_state: dict, gamification: dict):

    plan = (user_state.get("plan") or "FREE").upper()

    xp = 0
    streak = user_state.get("streak", 0)

    if isinstance(gamification, dict):
        xp_data = gamification.get("xp_gain", {})
        xp = xp_data.get("final_xp", 0) if isinstance(xp_data, dict) else 0

    # =========================
    # BASE NOTIFICATION LOGIC
    # =========================

    if xp == 0:
        return {
            "type": "neutral",
            "message": "Connecte ton activité pour commencer ta progression."
        }

    if xp < 10:
        return {
            "type": "info",
            "message": "Petite progression 👌 continue pour accélérer ton score."
        }

    if xp < 25:
        return {
            "type": "positive",
            "message": "🔥 Bonne dynamique ! Ton capital de progression augmente."
        }

    if xp < 50:
        return {
            "type": "strong_positive",
            "message": "🚀 Excellente activité ! Tu avances plus vite que la moyenne."
        }

    # =========================
    # STREAK BOOST MESSAGES
    # =========================

    if streak >= 7:
        return {
            "type": "streak",
            "message": "⚡ Streak actif ! Tu construis un avantage cumulatif."
        }

    if streak >= 14:
        return {
            "type": "elite_streak",
            "message": "💎 Momentum Elite ! Effet boule de neige actif."
        }

    # =========================
    # LIBERTY MODE
    # =========================

    if plan == "LIBERTY":
        return {
            "type": "liberty",
            "message": "🏆 LIBERTY MODE actif — système financier autonome en croissance."
        }

    return {
        "type": "default",
        "message": "Progression enregistrée."
    }
