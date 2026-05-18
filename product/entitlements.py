PLAN_ORDER = {
    "FREE": 0,
    "GOLD": 1,
    "ELITE": 2,
}

PLAN_ALIASES = {
    "FOUNDATION": "FREE",
    "GROWTH": "GOLD",
    "WEALTH_OS": "ELITE",
    "LIBERTY": "ELITE",
    "LIBERTY_LEGACY": "ELITE",
    "PLATINUM": "ELITE",
}

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
    "ELITE": {
        "name": "Wealth OS",
        "price": "79 EUR/mois",
        "promise": "Tu pilotes ton patrimoine comme un Family Office.",
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
            "basic_ai",
            "gamification",
        ],
        "features": [
            "simple_wealth_view",
            "income_expense_tracking",
            "basic_progression",
            "basic_missions",
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
            "advanced_ai",
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
            "advanced_ai",
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
            "premium_ai",
            "advanced_allocations",
            "governance",
            "automatic_imports",
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
        "description": "Analyser business, startup, franchise et AI business.",
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
        "key": "advanced_ai",
        "label": "IA avancee",
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
]


def normalize_plan(plan: str | None) -> str:
    value = (plan or "FREE").upper()
    return PLAN_ALIASES.get(value, value if value in PLAN_ORDER else "FREE")


def plan_allows(current_plan: str, required_plan: str) -> bool:
    return PLAN_ORDER[normalize_plan(current_plan)] >= PLAN_ORDER[normalize_plan(required_plan)]


def build_entitlements(plan: str):
    normalized = normalize_plan(plan)
    return {
        "plan": normalized,
        "copy": PLAN_COPY[normalized],
        **PLAN_ENTITLEMENTS[normalized],
    }


def can_access_module(plan: str, score: int, module: dict) -> bool:
    return plan_allows(plan, module["min_plan"]) and score >= int(module.get("min_score", 0))
