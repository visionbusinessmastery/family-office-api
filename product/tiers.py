PLAN_ORDER = {
    "FREE": 0,
    "GOLD": 1,
    "ELITE": 2,
    "LIBERTY": 3,
    "LEGACY": 4,
}

PLAN_ALIASES = {
    "FOUNDATION": "FREE",
    "SILVER": "FREE",
    "GROWTH": "GOLD",
    "PLATINUM": "ELITE",
    "WEALTH_OS": "ELITE",
    "LIBERTY_LEGACY": "LIBERTY",
    "HERITAGE": "LEGACY",
    "DYNASTY": "LEGACY",
    "DYNASTY_OFFICE": "LEGACY",
}

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due"}

FEATURE_MIN_PLAN = {
    "portfolio_basic": "FREE",
    "finance_tracking": "FREE",
    "basic_guidance": "FREE",
    "basic_progression": "FREE",
    "wealth_snapshot": "FREE",
    "next_milestone": "FREE",
    "future_intelligence_lite": "FREE",
    "ethan_limited": "FREE",
    "opportunity_discovery": "FREE",
    "real_estate_discovery": "FREE",
    "business_discovery": "FREE",
    "legacy_discovery": "FREE",
    "forex_limited": "FREE",
    "portfolio_advanced": "GOLD",
    "investment_tracking": "GOLD",
    "diversification": "GOLD",
    "category_opportunities": "GOLD",
    "cashflow_analysis": "GOLD",
    "yield_analysis": "GOLD",
    "trend_signals": "GOLD",
    "forex_full": "GOLD",
    "ethan_opportunities": "GOLD",
    "smart_recommendations": "GOLD",
    "future_intelligence_full": "GOLD",
    "wealth_narrative": "GOLD",
    "opportunity_radar": "GOLD",
    "weekly_email_insights": "GOLD",
    "family_office_scorecard": "GOLD",
    "hidden_wealth": "GOLD",
    "stress_tests": "GOLD",
    "dependency_detector": "GOLD",
    "strategic_intelligence": "GOLD",
    "advanced_analytics": "ELITE",
    "ethan_full_access": "ELITE",
    "priority_support": "ELITE",
    "multi_asset_strategy": "ELITE",
    "business_assets": "ELITE",
    "family_office_basic": "ELITE",
    "premium_opportunities": "ELITE",
    "premium_guidance": "ELITE",
    "wealth_consolidation": "ELITE",
    "wealth_blocks": "ELITE",
    "multi_scenario_simulations": "ELITE",
    "family_office_intelligence": "ELITE",
    "family_office_ceo": "ELITE",
    "advanced_wealth_narrative": "ELITE",
    "global_opportunities": "LIBERTY",
    "wealth_architecture": "LIBERTY",
    "sovereign_wealth": "LIBERTY",
    "international_strategy": "LIBERTY",
    "fiscal_optimization": "LIBERTY",
    "automation": "LIBERTY",
    "unlock_all": "LIBERTY",
    "child_accounts": "LIBERTY",
    "family_office_mode": "LIBERTY",
    "advanced_simulations": "LIBERTY",
    "advanced_strategic_arbitrage": "LIBERTY",
    "family_office_board": "LIBERTY",
    "allocation_priorities": "LIBERTY",
    "multi_goals": "LIBERTY",
    "transmission": "LIBERTY",
    "family_vault": "LEGACY",
    "heirs_mode": "LEGACY",
    "dynasty_features": "LEGACY",
    "legacy_dashboard": "LEGACY",
    "asset_protection": "LEGACY",
    "legacy_engine": "LEGACY",
    "trust_simulation": "LEGACY",
    "succession_planning": "LEGACY",
    "family_governance": "LEGACY",
}

DISCOVERABLE_MODULES = {
    "real_estate",
    "yield_assets",
    "venture_assets",
    "opportunities",
    "advanced_guidance",
    "family_vault",
    "heirs_mode",
    "protection_layer",
    "global_strategy",
    "legacy_timeline",
}


def normalize_plan(plan: str | None) -> str:
    value = str(plan or "FREE").strip().upper()
    return PLAN_ALIASES.get(value, value if value in PLAN_ORDER else "FREE")


def plan_rank(plan: str | None) -> int:
    return PLAN_ORDER[normalize_plan(plan)]


def plan_allows(current_plan: str | None, required_plan: str | None) -> bool:
    return plan_rank(current_plan) >= plan_rank(required_plan)


def highest_plan(*plans: str | None) -> str:
    normalized = [normalize_plan(plan) for plan in plans if plan]
    if not normalized:
        return "FREE"
    return max(normalized, key=plan_rank)


def resolve_effective_plan(
    user_plan: str | None,
    subscription_plan: str | None = None,
    subscription_status: str | None = None,
) -> str:
    if (
        subscription_plan
        and str(subscription_status or "").lower() in ACTIVE_SUBSCRIPTION_STATUSES
    ):
        return highest_plan(user_plan, subscription_plan)

    return normalize_plan(user_plan)


def is_feature_unlocked(user_plan: str, feature: str) -> bool:
    required_plan = FEATURE_MIN_PLAN.get(feature)
    if not required_plan:
        return False
    return plan_allows(user_plan, required_plan)


def unlocked_features_for_plan(user_plan: str) -> list[str]:
    plan = normalize_plan(user_plan)
    return sorted(
        feature
        for feature, required_plan in FEATURE_MIN_PLAN.items()
        if plan_allows(plan, required_plan)
    )
