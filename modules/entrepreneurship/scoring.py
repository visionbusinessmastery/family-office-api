# =========================
# SCORING ENGINE ENTREPRENEURSHIP
# =========================
def entrepreneurship_score(user_profile):

    score = 0

    if user_profile.get("has_business"):
        score += 40

    if user_profile.get("monthly_income", 0) > 3000:
        score += 20

    if user_profile.get("multiple_income_streams"):
        score += 40

    return min(score, 100)
