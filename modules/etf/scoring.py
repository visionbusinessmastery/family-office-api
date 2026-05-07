# =========================
# SCORING ENGINE ETF
# =========================
def etf_score(user_profile):

    score = 0

    savings = user_profile.get("savings", 0)

    if savings > 1000:
        score += 30

    if savings > 10000:
        score += 40

    if savings > 50000:
        score += 30

    return min(score, 100)
