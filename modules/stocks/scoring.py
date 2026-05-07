# =========================
# SCORING ENGINE STOCKS
# =========================
def stock_score(user_profile):

    score = 0

    capital = user_profile.get("capital", 0)

    risk = user_profile.get("risk_profile", "medium")

    if capital > 1000:
        score += 20

    if capital > 10000:
        score += 40

    if capital > 50000:
        score += 60

    if risk == "high":
        score += 20

    return min(score, 100)
