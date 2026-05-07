# =========================
# SCORING ENGINE CROWDFUNDING
# =========================
def crowdfunding_score(user_profile):

    score = 0

    capital = user_profile.get("capital", 0)

    if capital > 500:
        score += 30

    if capital > 5000:
        score += 40

    if capital > 20000:
        score += 30

    return min(score, 100)
