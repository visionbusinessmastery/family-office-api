# =========================
# AI RISK ENGINE
# =========================

def compute_risk_profile(context: dict):

    portfolio_value = context.get("portfolio_value", 0)
    crypto_ratio = context.get("crypto_ratio", 0)
    savings = context.get("savings", 0)

    score = 50

    if crypto_ratio > 0.5:
        score += 25

    if savings < 1000:
        score += 15

    if portfolio_value > 100000:
        score -= 10

    score = max(0, min(score, 100))

    if score >= 75:
        level = "HIGH RISK"

    elif score >= 45:
        level = "MEDIUM RISK"

    else:
        level = "LOW RISK"

    return {
        "risk_score": score,
        "risk_level": level
    }
