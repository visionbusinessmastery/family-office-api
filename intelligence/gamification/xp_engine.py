# =========================
# XP ENGINE
# =========================

def compute_xp(action, streak=0, liberty_mode=False):

    base_xp = {
        "view_dashboard": 10,
        "complete_profile": 50,
        "add_asset": 25,
        "investment_completed": 100
    }

    xp = base_xp.get(action, 5)

    # BONUS STREAK
    xp += streak * 2

    # BONUS LIBERTY
    if liberty_mode:
        xp *= 2

    return int(xp)
