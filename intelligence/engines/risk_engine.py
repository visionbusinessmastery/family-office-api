# =========================
# AI RISK ENGINE (FIXED + SAAS READY)
# =========================

def compute_risk_profile(context: dict):

    portfolio = context.get("portfolio", []) or []
    profile = context.get("profile", {}) or {}

    # =========================
    # SAFE DEFAULTS
    # =========================
    total_value = 0
    crypto_value = 0

    # =========================
    # PORTFOLIO ANALYSIS
    # =========================
    for asset in portfolio:

        if not isinstance(asset, dict):
            continue

        value = float(asset.get("value", 0) or 0)
        asset_type = (asset.get("type") or "").lower()

        total_value += value

        if asset_type == "crypto":
            crypto_value += value

    crypto_ratio = (crypto_value / total_value) if total_value > 0 else 0

    # =========================
    # PROFILE INPUTS
    # =========================
    savings = float(profile.get("epargne", 0) or 0)

    # =========================
    # BASE SCORE
    # =========================
    score = 50

    # =========================
    # CRYPTO RISK
    # =========================
    if crypto_ratio > 0.5:
        score += 25
    elif crypto_ratio > 0.3:
        score += 15

    # =========================
    # SAVINGS SAFETY
    # =========================
    if savings < 1000:
        score += 15
    elif savings > 10000:
        score -= 10

    # =========================
    # PORTFOLIO SIZE (STABILITY BONUS)
    # =========================
    if total_value > 100000:
        score -= 10
    elif total_value < 5000:
        score += 10

    # =========================
    # CLAMP
    # =========================
    score = max(0, min(score, 100))

    # =========================
    # LEVEL SYSTEM
    # =========================
    if score >= 75:
        level = "HIGH RISK"
    elif score >= 45:
        level = "MEDIUM RISK"
    else:
        level = "LOW RISK"

    # =========================
    # RETURN
    # =========================
    return {
        "risk_score": score,
        "risk_level": level,
        "crypto_ratio": round(crypto_ratio, 3),
        "portfolio_value": round(total_value, 2)
    }
