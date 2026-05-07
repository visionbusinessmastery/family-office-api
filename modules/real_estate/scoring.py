# =========================
# SCORING ENGINE REAL ESTATE
# =========================
def real_estate_score(user_profile):

    score = 0

    savings = user_profile.get("savings", 0)

    if savings > 5000:
        score += 20

    if savings > 20000:
        score += 40

    if savings > 100000:
        score += 40

    return min(score, 100)
