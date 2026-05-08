
# =========================
# BUILD DASHBOARD USER (UI LAYER ONLY - CLEAN ARCHITECTURE)
# =========================

def build_dashboard(user, intelligence):

    # =========================
    # SAFE INPUTS
    # =========================
    if not isinstance(user, dict):
        user = {}

    if not isinstance(intelligence, dict):
        intelligence = {}

    plan = (user.get("plan") or "FREE").upper()

    # =========================
    # SAFE SCORE PARSING
    # =========================
    score_data = intelligence.get("score")

    if isinstance(score_data, dict):
        score = float(score_data.get("score") or 0)
    else:
        score = float(score_data or 0)

    level = intelligence.get("level") or "BEGINNER"

    # =========================
    # DASHBOARD BASE STRUCTURE (UI ONLY)
    # =========================
    dashboard = {
        "hero": True,
        "score_card": True,
        "upgrade_banner": plan == "FREE",
        "plan": plan,
        "level": level,
        "score": score,
        "features": [],
        "ai_blocks": [],
        "locked_blocks": [],
        "mode": "STANDARD"
    }

    # =========================
    # 🧱 PLAN SYSTEM (UI ONLY)
    # =========================

    if plan == "FREE":

        dashboard["features"] = [
            "basic_portfolio",
            "education_content"
        ]

        dashboard["locked_blocks"] = [
            "ai_analysis",
            "advanced_portfolio",
            "wealth_optimizer",
            "ai_advisor"
        ]

    elif plan == "SILVER":

        dashboard["features"] = [
            "portfolio_view",
            "basic_insights",
            "market_overview"
        ]

        dashboard["locked_blocks"] = [
            "ai_advisor",
            "advanced_strategies"
        ]

    elif plan == "GOLD":

        dashboard["features"] = [
            "full_portfolio",
            "market_insights",
            "ai_recommendations"
        ]

        dashboard["ai_blocks"] = [
            "market_ai",
            "recommendation_engine"
        ]

    elif plan == "ELITE":

        dashboard["features"] = [
            "full_ai_suite",
            "private_deals_access",
            "family_office_mode"
        ]

        dashboard["ai_blocks"] = [
            "predictive_engine",
            "elite_ai_coach",
            "family_office_ai"
        ]

    elif plan == "LIBERTY":

        dashboard["features"] = [
            "wealth_os",
            "autopilot_engine",
            "private_deals",
            "full_ai_coach",
            "family_office_mode"
        ]

        dashboard["ai_blocks"] = [
            "liberty_ai_coach",
            "autonomous_portfolio_engine",
            "wealth_prediction_engine",
            "family_office_ai"
        ]

        dashboard["mode"] = "LIBERTY_OPERATING_SYSTEM"
        dashboard["unlock_all"] = True

        dashboard["ai_blocks"].append("autopilot_wealth_engine")

    # =========================
    # 📈 SCORE BOOST (UI ENRICHMENT ONLY)
    # =========================

    if score >= 50:
        dashboard["ai_blocks"].append("smart_insights")

    if score >= 70:
        dashboard["ai_blocks"].append("opportunity_engine")

    if score >= 1000:
        dashboard["ai_blocks"].append("xp_engine_boost")

    if score >= 3000:
        dashboard["ai_blocks"].append("advanced_ai_coach")

    if score >= 7000:
        dashboard["ai_blocks"].append("elite_mode")

    if score >= 15000:
        dashboard["ai_blocks"].append("liberty_overdrive")

    # =========================
    # CLEAN OUTPUT
    # =========================
    dashboard["features"] = list(set(dashboard["features"]))
    dashboard["ai_blocks"] = list(set(dashboard["ai_blocks"]))
    dashboard["locked_blocks"] = list(set(dashboard["locked_blocks"]))

    return dashboard
