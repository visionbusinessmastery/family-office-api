# =========================
# SCORING ENGINE STARTUP
# =========================
def startup_score(user_profile):

    score = 0

    entrepreneurship = user_profile.get("entrepreneurship_level", 0)

    score += min(entrepreneurship * 10, 60)

    if user_profile.get("networking", False):
        score += 20

    if user_profile.get("startup_interest", False):
        score += 20

    return min(score, 100)
