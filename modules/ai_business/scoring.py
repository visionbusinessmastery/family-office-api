# =========================
# SCORING ENGINE AI BUSINESS
# =========================
def ai_business_score(user_profile):

    score = 0

    ai_interest = user_profile.get("ai_interest", False)
    business_experience = user_profile.get("business_experience", 0)

    if ai_interest:
        score += 40

    if business_experience > 2:
        score += 30

    if business_experience > 5:
        score += 30

    return min(score, 100)
