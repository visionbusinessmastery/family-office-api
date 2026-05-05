# =========================
# BUILD DASHBOARD USER (PRODUCTION READY)
# =========================

def build_dashboard(user, intelligence):
    """
    Génère la structure du dashboard utilisateur
    basée sur le plan + intelligence + score IA.
    """

    # =========================
    # SAFE INPUTS
    # =========================
    if not isinstance(user, dict):
        user = {}

    if not isinstance(intelligence, dict):
        intelligence = {}

    plan = (user.get("plan") or "FREE").upper()

    # =========================
    # SAFE INTELLIGENCE PARSING
    # =========================
    score_data = intelligence.get("score")

    if isinstance(score_data, dict):
        score = float(score_data.get("score") or 0)
    else:
        score = float(score_data or 0)

    level = intelligence.get("level") or "BEGINNER"

    # =========================
    # BASE DASHBOARD STRUCTURE
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
        "locked_blocks": []
    }

    # =========================
    # 1. PLAN-BASED DASHBOARD
    # =========================
    if plan == "FREE":
        dashboard["features"] = [
            "basic_portfolio",
            "education_content"
        ]

        dashboard["locked_blocks"] = [
            "ai_analysis",
            "advanced_portfolio",
            "wealth_optimizer"
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

    elif plan == "ELITE":
        dashboard["features"] = [
            "everything",
            "private_deals_access",
            "full_ai_suite"
        ]

        dashboard["ai_blocks"] = [
            "full_ai_advisor",
            "predictive_engine",
            "family_office_mode"
        ]

    # =========================
    # 2. SCORE-BASED ENHANCEMENTS
    # =========================
    if score >= 50:
        dashboard["ai_blocks"].append("smart_insights")

    if score >= 70:
        dashboard["ai_blocks"].append("opportunity_engine")

    if score >= 80:
        dashboard["ai_blocks"].append("elite_insight_banner")

    if score >= 90:
        dashboard["ai_blocks"].append("wealth_mastery_mode")

    # =========================
    # 3. CLEAN OUTPUT (NO DUPLICATES)
    # =========================
    dashboard["ai_blocks"] = list(set(dashboard["ai_blocks"]))
    dashboard["features"] = list(set(dashboard["features"]))
    dashboard["locked_blocks"] = list(set(dashboard["locked_blocks"]))

    return dashboard
