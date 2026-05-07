# =========================
# SCORING ENGINE TRADING
# =========================
def trading_score(user_profile):

    score = 0

    risk = user_profile.get("risk_profile", "low")

    if risk == "medium":
        score += 30

    if risk == "high":
        score += 60

    experience = user_profile.get("trading_experience", 0)

    score += min(experience * 5, 40)

    return min(score, 100)
