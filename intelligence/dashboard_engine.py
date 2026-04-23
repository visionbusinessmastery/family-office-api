# =========================
# BUILD DASHBOARD USER
# =========================
def build_dashboard(user, intelligence):

    plan = user.get("plan", "FREE")
    score = intelligence["score"]["score"]
    segment = intelligence["segment"]

    dashboard = {
        "hero": True,
        "score_card": True,
        "upgrade_banner": False,
        "features": [],
        "ai_blocks": [],
        "locked_blocks": []
    }

    # =========================
    # FREE USERS
    # =========================
    if plan == "FREE":

        dashboard["upgrade_banner"] = True

        dashboard["features"] = [
            "basic_portfolio",
            "education_content"
        ]

        dashboard["locked_blocks"] = [
            "ai_analysis",
            "advanced_portfolio",
            "opportunities"
        ]

    # =========================
    # SILVER
    # =========================
    elif plan == "SILVER":

        dashboard["features"] = [
            "portfolio_view",
            "basic_insights"
        ]

        if score > 60:
            dashboard["ai_blocks"].append("basic_ai_insights")

        dashboard["locked_blocks"] = [
            "advanced_ai",
            "full_portfolio"
        ]

    # =========================
    # GOLD
    # =========================
    elif plan == "GOLD":

        dashboard["features"] = [
            "full_portfolio",
            "investment_tracking",
            "market_insights"
        ]

        if segment in ["ADVANCED", "ELITE_INVESTOR"]:
            dashboard["ai_blocks"].append("ai_opportunities")

    # =========================
    # ELITE
    # =========================
    elif plan == "ELITE":

        dashboard["features"] = [
            "everything"
        ]

        dashboard["ai_blocks"] = [
            "full_ai_advisor",
            "investment_recommendations",
            "macro_analysis",
            "deal_flow_engine"
        ]

    # =========================
    # DYNAMIC RULES (INTELLIGENCE BONUS)
    # =========================
    if score >= 80:
        dashboard["ai_blocks"].append("elite_insight_banner")

    if segment == "BEGINNER":
        dashboard["locked_blocks"].append("simplicity_mode")

    return dashboard
