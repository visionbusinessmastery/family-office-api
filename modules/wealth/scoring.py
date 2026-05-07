# =========================
# SCORING ENGINE WEALTH
# =========================
def wealth_score(user_profile):

    score = 0

    income = user_profile.get("monthly_income", 0)
    savings = user_profile.get("savings", 0)
    investments = user_profile.get("investments", 0)

    score += income * 0.01
    score += savings * 0.02
    score += investments * 0.03

    return min(int(score), 100)
