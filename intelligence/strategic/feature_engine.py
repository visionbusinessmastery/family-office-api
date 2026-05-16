
# =========================
# COMPUTE FEATURE ACCESS (PRODUCTION READY)
# =========================

def compute_feature_access(profile: dict, score_data: dict, usage: dict = None):
    """
    Détermine les features accessibles selon :
    - plan utilisateur
    - score financier
    - richesse (assets)
    - engagement utilisateur
    """

    # =========================
    # SAFE INPUTS
    # =========================
    if not isinstance(profile, dict):
        profile = {}

    if not isinstance(score_data, dict):
        score_data = {}

    if not isinstance(usage, dict):
        usage = {}

    plan = (profile.get("plan") or "FREE").upper()

    score = float(score_data.get("score") or 0)

    savings = float(profile.get("savings") or 0)
    investments = float(profile.get("investments") or 0)

    total_assets = savings + investments

    # =========================
    # FEATURES SET (NO DUPLICATES)
    # =========================
    features = set()

    # =========================
    # 1. PLAN-BASED FEATURES
    # =========================
    if plan in ["SILVER", "GOLD", "ELITE"]:
        features.add("portfolio_basic")

    if plan in ["GOLD", "ELITE"]:
        features.add("portfolio_advanced")
        features.add("investment_tracking")

    if plan == "ELITE":
        features.add("ai_full_access")
        features.add("priority_support")

    # =========================
    # 2. SCORE-BASED FEATURES
    # =========================
    if score >= 50:
        features.add("smart_recommendations")

    if score >= 70:
        features.add("ai_opportunities")

    if score >= 85:
        features.add("elite_insights")

    # =========================
    # 3. WEALTH-BASED FEATURES
    # =========================
    if total_assets > 10000:
        features.add("wealth_tracking")

    if total_assets > 50000:
        features.add("wealth_analytics")

    if total_assets > 100000:
        features.add("private_deals")

    if total_assets > 250000:
        features.add("family_office_mode")

    # =========================
    # 4. ENGAGEMENT FEATURES
    # =========================
    login_count = int(usage.get("login_count") or 0)

    if login_count > 5:
        features.add("loyal_user_bonus")

    if login_count > 20:
        features.add("power_user_mode")

    # =========================
    # 5. CLEAN OUTPUT
    # =========================
    return sorted(list(features))
