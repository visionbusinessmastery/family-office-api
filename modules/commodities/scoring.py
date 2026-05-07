# =========================
# SCORING ENGINE COMMODITIES
# =========================
def commodities_score(user_profile):

    diversification = user_profile.get("diversification", 0)

    score = diversification * 10

    return min(score, 100)
