# =========================
# SCORING ENGINE MARKET
# =========================
def market_score(user_profile):

    score = 0

    experience = user_profile.get("experience", "low")

    if experience == "low":
        score += 20

    elif experience == "medium":
        score += 50

    else:
        score += 80

    return min(score, 100)
