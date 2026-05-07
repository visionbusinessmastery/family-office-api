# =========================
# SCORING ENGINE CRYPTO
# =========================
def crypto_score(user_profile):

    score = 0

    risk = user_profile.get("risk_profile", "low")

    if risk == "medium":
        score += 40

    if risk == "high":
        score += 70

    experience = user_profile.get("crypto_experience", 0)

    score += min(experience * 5, 30)

    return min(score, 100)
