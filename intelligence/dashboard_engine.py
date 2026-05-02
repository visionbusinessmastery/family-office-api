# =========================
# BUILD DASHBOARD USER
# =========================
def build_dashboard(user, intelligence):

    plan = user.get("plan", "FREE")

    score = 0
    segment = "BEGINNER"

    if isinstance(intelligence, dict):
        score = intelligence.get("score", {}).get("score", 0)
        segment = intelligence.get("level", "BEGINNER")

    dashboard = {
        "hero": True,
        "score_card": True,
        "upgrade_banner": plan == "FREE",
        "features": [],
        "ai_blocks": [],
        "locked_blocks": []
    }

    if plan == "FREE":
        dashboard["features"] = ["basic_portfolio", "education_content"]
        dashboard["locked_blocks"] = ["ai_analysis", "advanced_portfolio"]

    elif plan == "SILVER":
        dashboard["features"] = ["portfolio_view", "basic_insights"]

    elif plan == "GOLD":
        dashboard["features"] = ["full_portfolio", "market_insights"]

    elif plan == "ELITE":
        dashboard["features"] = ["everything"]
        dashboard["ai_blocks"] = ["full_ai_advisor"]

    if score >= 80:
        dashboard["ai_blocks"].append("elite_insight_banner")

    return dashboard
