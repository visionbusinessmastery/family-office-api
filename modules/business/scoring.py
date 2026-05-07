# =========================
# SCORING ENGINE BUSINESS
# =========================
def business_score(user_profile):

    score = 0

    revenue = user_profile.get("monthly_income", 0)

    if revenue > 1000:
        score += 20

    if revenue > 5000:
        score += 30

    if revenue > 10000:
        score += 50

    return min(score, 100)
