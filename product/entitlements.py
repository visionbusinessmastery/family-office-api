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

PLAN_COPY = {
    "FREE": {
        "name": "Foundation",
        "price": "0 EUR/mois",
        "promise": "Tu construis tes fondations financieres.",
    },
    "GOLD": {
        "name": "Growth",
        "price": "29 EUR/mois",
        "promise": "Tu entres en phase de croissance patrimoniale.",
    },
    "SILVER": {
        "name": "Foundation Plus",
        "price": "legacy",
        "promise": "Tu consolides tes fondations financieres.",
    },
    "PLATINUM": {
        "name": "Advanced Growth",
        "price": "legacy",
        "promise": "Tu acceleres avec des analytics avancees.",
    },
    "ELITE": {
        "name": "Wealth OS",
        "price": "79 EUR/mois",
        "promise": "Tu pilotes ton patrimoine comme un Family Office.",
    },
    "LIBERTY": {
        "name": "Sovereign Wealth",
        "price": "sur mesure",
        "promise": "Tu preserves, multiplies et transmets ta liberte patrimoniale.",
    },
    "LEGACY": {
        "name": "Dynasty Office",
        "price": "sur mesure",
        "promise": "Tu construis une architecture patrimoniale qui peut te survivre.",
    },
}

PLAN_ENTITLEMENTS = {
    "FREE": {
        "max_assets": 5,
        "ai_level": "basic",
        "modules": [
            "foundation",
            "finance",
            "portfolio",
            "basic_score",
            "basic_guidance",
            "gamification",
        ],
        "features": [
            "simple_wealth_view",
            "income_expense_tracking",
            "basic_progression",
            "basic_missions",
            "forex_limited",
        ],
    },
    "GOLD": {
        "max_assets": 50,
        "ai_level": "advanced",
        "modules": [
            "foundation",
            "finance",
            "portfolio",
            "diversification",
            "real_estate",
            "yield_assets",
            "venture_assets",
            "analytics",
            "command_center",
            "opportunities",
            "advanced_guidance",
            "gamification",
        ],
        "features": [
            "advanced_portfolio",
            "real_estate",
            "business_assets",
            "portfolio_chart",
            "smart_notifications",
            "category_opportunities",
            "projections",
            "forex_full",
        ],
    },
    "SILVER": {
        "max_assets": 15,
        "ai_level": "standard",
        "modules": [
            "foundation",
            "finance",
            "portfolio",
            "basic_score",
            "basic_guidance",
            "gamification",
        ],
        "features": [
            "simple_wealth_view",
            "income_expense_tracking",
            "basic_progression",
            "basic_missions",
            "forex_limited",
        ],
    },
    "PLATINUM": {
        "max_assets": 100,
        "ai_level": "advanced",
        "modules": [
            "foundation",
            "finance",
            "portfolio",
            "diversification",
            "real_estate",
            "yield_assets",
            "venture_assets",
            "analytics",
            "command_center",
            "opportunities",
            "advanced_guidance",
            "gamification",
        ],
        "features": [
            "advanced_portfolio",
            "real_estate",
            "business_assets",
            "portfolio_chart",
            "smart_notifications",
            "category_opportunities",
            "projections",
            "forex_full",
        ],
    },
    "ELITE": {
        "max_assets": None,
        "ai_level": "premium",
        "modules": [
            "foundation",
            "finance",
            "portfolio",
            "diversification",
            "real_estate",
            "yield_assets",
            "venture_assets",
            "analytics",
            "command_center",
            "opportunities",
            "advanced_guidance",
            "multi_user",
            "bank_sync",
            "governance",
            "imports",
            "gamification",
        ],
        "features": [
            "multi_user",
            "companies",
            "wealth_consolidation",
            "banking_apis",
            "live_sync",
            "premium_guidance",
            "advanced_allocations",
            "governance",
            "automatic_imports",
            "forex_advanced_analytics",
        ],
    },
    "LIBERTY": {
        "max_assets": None,
        "ai_level": "sovereign",
        "modules": [
            "foundation",
            "finance",
            "portfolio",
            "diversification",
            "real_estate",
            "yield_assets",
            "venture_assets",
            "analytics",
            "command_center",
            "opportunities",
            "advanced_guidance",
            "multi_user",
            "bank_sync",
            "governance",
            "imports",
            "automation",
            "legacy_planning",
            "gamification",
        ],
        "features": [
            "multi_user",
            "companies",
            "wealth_consolidation",
            "banking_apis",
            "live_sync",
            "sovereign_guidance",
            "advanced_allocations",
            "governance",
            "automatic_imports",
            "wealth_architecture",
            "legacy_planning",
            "forex_advanced_analytics",
        ],
    },
    "LEGACY": {
        "max_assets": None,
        "ai_level": "dynasty",
        "modules": [
            "foundation",
            "finance",
            "portfolio",
            "diversification",
            "real_estate",
            "yield_assets",
            "venture_assets",
            "analytics",
            "command_center",
            "opportunities",
            "advanced_guidance",
            "multi_user",
            "bank_sync",
            "governance",
            "imports",
            "automation",
            "family_vault",
            "heirs_mode",
            "protection_layer",
            "global_strategy",
            "legacy_timeline",
            "gamification",
        ],
        "features": [
            "multi_user",
            "companies",
            "wealth_consolidation",
            "banking_apis",
            "live_sync",
            "dynasty_guidance",
            "advanced_allocations",
            "governance",
            "automatic_imports",
            "wealth_architecture",
            "family_vault",
            "heirs_mode",
            "asset_protection",
            "global_strategy",
            "legacy_timeline",
            "forex_advanced_analytics",
        ],
    },
}

MODULE_REGISTRY = [
    {
        "key": "foundation",
        "label": "Foundation View",
        "stage": 1,
        "min_plan": "FREE",
        "min_score": 0,
        "description": "Vue claire de ta situation financiere globale.",
    },
    {
        "key": "finance",
        "label": "Revenus / charges",
        "stage": 1,
        "min_plan": "FREE",
        "min_score": 0,
        "description": "Piloter cashflow, epargne et dettes.",
    },
    {
        "key": "portfolio",
        "label": "Portefeuille",
        "stage": 1,
        "min_plan": "FREE",
        "min_score": 0,
        "description": "Centraliser tes premiers actifs financiers.",
    },
    {
        "key": "diversification",
        "label": "Exposition",
        "stage": 2,
        "min_plan": "GOLD",
        "min_score": 35,
        "description": "Voir les concentrations et arbitrages prioritaires.",
    },
    {
        "key": "forex",
        "label": "Forex / Currencies",
        "stage": 2,
        "min_plan": "FREE",
        "min_score": 0,
        "description": "Suivre une exposition simple aux devises sans interface de trading.",
    },
    {
        "key": "real_estate",
        "label": "Immobilier",
        "stage": 3,
        "min_plan": "GOLD",
        "min_score": 45,
        "description": "Piloter biens, rendement et plus-value potentielle.",
    },
    {
        "key": "yield_assets",
        "label": "Prets & Private Equity",
        "stage": 3,
        "min_plan": "GOLD",
        "min_score": 45,
        "description": "Suivre capital prete, rendement et valeur finale.",
    },
    {
        "key": "venture_assets",
        "label": "Business Cockpit",
        "stage": 4,
        "min_plan": "GOLD",
        "min_score": 55,
        "description": "Analyser business, startup, franchise et activites digitales.",
    },
    {
        "key": "command_center",
        "label": "Command Center",
        "stage": 5,
        "min_plan": "GOLD",
        "min_score": 60,
        "description": "Prioriser risques, opportunites et prochaines actions.",
    },
    {
        "key": "opportunities",
        "label": "Opportunites",
        "stage": 5,
        "min_plan": "GOLD",
        "min_score": 50,
        "description": "Recevoir des signaux personnalises par rubrique patrimoniale.",
    },
    {
        "key": "advanced_guidance",
        "label": "Guidance avancee",
        "stage": 5,
        "min_plan": "GOLD",
        "min_score": 50,
        "description": "Transformer ton contexte en actions prioritaires.",
    },
    {
        "key": "multi_user",
        "label": "Multi-user",
        "stage": 6,
        "min_plan": "ELITE",
        "min_score": 70,
        "description": "Partager le pilotage patrimonial avec ton equipe/famille.",
    },
    {
        "key": "bank_sync",
        "label": "Synchronisation live",
        "stage": 7,
        "min_plan": "ELITE",
        "min_score": 80,
        "description": "Architecture preparee pour connexions bancaires et imports.",
    },
    {
        "key": "legacy_planning",
        "label": "Legacy Planning",
        "stage": 8,
        "min_plan": "LIBERTY",
        "min_score": 85,
        "description": "Gouvernance avancee, transmission et architecture patrimoniale.",
    },
    {
        "key": "family_vault",
        "label": "Family Vault",
        "stage": 9,
        "min_plan": "LEGACY",
        "min_score": 0,
        "description": "Coffre-fort familial, documents, succession et notes privees.",
    },
    {
        "key": "heirs_mode",
        "label": "Heirs Mode",
        "stage": 9,
        "min_plan": "LEGACY",
        "min_score": 0,
        "description": "Preparation des heritiers, education financiere et Ethan Junior.",
    },
    {
        "key": "protection_layer",
        "label": "Protection Layer",
        "stage": 9,
        "min_plan": "LEGACY",
        "min_score": 0,
        "description": "Vulnerabilite, concentration, inflation lifestyle et protection patrimoniale.",
    },
    {
        "key": "global_strategy",
        "label": "Global Strategy",
        "stage": 9,
        "min_plan": "LEGACY",
        "min_score": 0,
        "description": "Diversification geographique, residence fiscale et strategie internationale.",
    },
    {
        "key": "legacy_timeline",
        "label": "Legacy Timeline",
        "stage": 9,
        "min_plan": "LEGACY",
        "min_score": 0,
        "description": "Projection 10 ans, 20 ans et vision generationnelle.",
    },
]


def normalize_plan(plan: str | None) -> str:
    value = (plan or "FREE").upper()
    return PLAN_ALIASES.get(value, value if value in PLAN_ORDER else "FREE")


def plan_rank(plan: str | None) -> int:
    return PLAN_ORDER[normalize_plan(plan)]


def plan_allows(current_plan: str, required_plan: str) -> bool:
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


def inherited_values(plan: str, field: str):
    normalized = normalize_plan(plan)
    values = []

    for candidate, entitlements in PLAN_ENTITLEMENTS.items():
        if plan_allows(normalized, candidate):
            for value in entitlements.get(field, []):
                if value not in values:
                    values.append(value)

    return values


def build_entitlements(plan: str):
    normalized = normalize_plan(plan)
    base = dict(PLAN_ENTITLEMENTS[normalized])
    base["modules"] = inherited_values(normalized, "modules")
    base["features"] = inherited_values(normalized, "features")

    return {
        "plan": normalized,
        "copy": PLAN_COPY[normalized],
        **base,
    }


def can_access_module(plan: str, score: int, module: dict) -> bool:
    normalized = normalize_plan(plan)
    required = normalize_plan(module["min_plan"])

    if plan_allows(normalized, "LIBERTY"):
        return True

    return plan_allows(normalized, required) and score >= int(module.get("min_score", 0))
