from fastapi import APIRouter
from product.entitlements import normalize_plan, plan_rank
router = APIRouter()

# =========================
# BUILD DASHBOARD (UI ONLY)
# =========================
def build_dashboard(user, intelligence):

    if not isinstance(user, dict):
        user = {}

    if not isinstance(intelligence, dict):
        intelligence = {}

    plan = normalize_plan(user.get("plan"))
    level_rank = plan_rank(plan)

    score_data = intelligence.get("score")

    if isinstance(score_data, dict):
        score = float(score_data.get("score") or 0)
    else:
        score = float(score_data or 0)

    level = intelligence.get("level") or "BEGINNER"

    dashboard = {
        "hero": True,
        "score_card": True,
        "upgrade_banner": plan == "FREE",
        "plan": plan,
        "level": level,
        "score": score,
        "features": [],
        "ethan_blocks": [],
        "locked_blocks": [],
        "mode": "STANDARD"
    }

    if level_rank >= 0:
        dashboard["features"] = ["basic_portfolio", "education_content"]

    if level_rank == 0:
        dashboard["locked_blocks"] = [
            "ethan_analysis",
            "advanced_portfolio",
            "wealth_optimizer",
            "ethan_advisor"
        ]

    if level_rank >= 1:
        dashboard["features"] += [
            "full_portfolio",
            "market_insights",
            "ethan_recommendations"
        ]
        dashboard["ethan_blocks"] += [
            "market_signals",
            "recommendation_engine"
        ]

    if level_rank >= 2:
        dashboard["features"] += [
            "full_ethan_suite",
            "private_deals_access",
            "family_office_mode"
        ]
        dashboard["ethan_blocks"] += [
            "predictive_engine",
            "elite_guidance",
            "family_office_guidance"
        ]

    if level_rank >= 3:
        dashboard["features"] += [
            "wealth_os",
            "autopilot_engine",
            "private_deals",
            "full_ethan_guidance",
            "family_office_mode"
        ]
        dashboard["ethan_blocks"] += [
            "liberty_guidance",
            "autonomous_portfolio_engine",
            "wealth_prediction_engine",
            "family_office_guidance"
        ]

        dashboard["mode"] = "LIBERTY_OPERATING_SYSTEM"
        dashboard["unlock_all"] = True
        dashboard["locked_blocks"] = []

    if level_rank >= 4:
        dashboard["features"] += [
            "family_vault",
            "heirs_mode",
            "protection_layer",
            "global_strategy",
            "legacy_timeline",
            "dynasty_office"
        ]
        dashboard["ethan_blocks"] += [
            "legacy_guardian",
            "dynasty_stability",
            "succession_readiness",
            "family_governance_index",
            "asset_protection_index"
        ]
        dashboard["mode"] = "DYNASTY_OFFICE"
        dashboard["unlock_all"] = True
        dashboard["locked_blocks"] = []

    if score >= 50:
        dashboard["ethan_blocks"].append("smart_insights")

    if score >= 70:
        dashboard["ethan_blocks"].append("opportunity_engine")

    if score >= 1000:
        dashboard["ethan_blocks"].append("xp_engine_boost")

    if score >= 3000:
        dashboard["ethan_blocks"].append("advanced_guidance")

    if score >= 7000:
        dashboard["ethan_blocks"].append("elite_mode")

    if score >= 15000:
        dashboard["ethan_blocks"].append("liberty_overdrive")

    dashboard["features"] = list(set(dashboard["features"]))
    dashboard["ethan_blocks"] = list(set(dashboard["ethan_blocks"]))
    dashboard["locked_blocks"] = list(set(dashboard["locked_blocks"]))

    return dashboard

