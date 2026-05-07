# =========================
# SCORING ENGINE FRANCHISE
# =========================
def franchise_score(user_profile):

    score = 0

    capital = user_profile.get("capital", 0)

    if capital > 10000:
        score += 30

    if capital > 50000:
        score += 40

    if capital > 100000:
        score += 30

    return min(score, 100)
