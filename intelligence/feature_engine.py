
# =========================
# COMPUTE FEATURE ACCESS
# =========================
def compute_feature_access(profile: dict, score_data: dict, usage: dict = None):

    plan = profile.get("plan", "FREE")
    score = score_data.get("score", 0)

    savings = profile.get("savings", 0) or 0
    investments = profile.get("investments", 0) or 0

    total_assets = savings + investments

    # =========================
    # BASE FEATURES (plan)
    # =========================
    features = []

    if plan in ["SILVER", "GOLD", "ELITE"]:
        features.append("portfolio_basic")

    if plan in ["GOLD", "ELITE"]:
        features.append("portfolio_advanced")
        features.append("investment_tracking")

    if plan == "ELITE":
        features.append("ai_full_access")

    # =========================
    # SMART UNLOCK (behavior)
    # =========================

    if score >= 60:
        features.append("smart_recommendations")

    if score >= 75:
        features.append("ai_opportunities")

    if total_assets > 50000:
        features.append("wealth_analytics")

    if total_assets > 100000:
        features.append("private_deals")

    # =========================
    # ENGAGEMENT (optionnel futur)
    # =========================
    if usage:
        if usage.get("login_count", 0) > 10:
            features.append("loyal_user_bonus")

    return list(set(features))
