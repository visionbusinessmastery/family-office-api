# =========================
# SCORING ENGINE STOCKS
# =========================

def stocks_score(user_profile: dict):

    score = 0

    capital = user_profile.get("capital", 0)
    risk = (user_profile.get("risk_profile", "medium") or "medium").lower()

    # =========================
    # CAPITAL SCORE
    # =========================
    if capital > 1000:
        score += 20

    if capital > 10000:
        score += 40

    if capital > 50000:
        score += 60

    # =========================
    # RISK BONUS
    # =========================
    if risk == "high":
        score += 20

    return min(score, 100)
