def compute_xp(action, streak=0, liberty_mode=False):

    base_xp = {
        "view_dashboard": 10,
        "complete_profile": 50,
        "add_asset": 25,
        "investment_completed": 100,
        "add_income": 30,
        "add_expense": 20,
        "ask_ai_coach": 15,
    }

    # =========================
    # BASE XP
    # =========================
    xp = base_xp.get(action, 5)

    # =========================
    # STREAK BONUS (CAP SAFE)
    # =========================
    streak_bonus = min(streak * 2, 30)  # cap anti-explosion
    xp += streak_bonus

    # =========================
    # LIBERTY MODE MULTIPLIER (SAFE)
    # =========================
    if liberty_mode:
        xp = int(xp * 1.5)  # au lieu de x2 (moins inflationniste)

    # =========================
    # FINAL SAFETY CAP
    # =========================
    return min(int(xp), 200)
