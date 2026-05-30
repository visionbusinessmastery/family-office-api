from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from intelligence.gamification.progress_service import award_xp
from intelligence.user_intelligence_engine import compute_user_intelligence
from product.entitlements import (
    MODULE_REGISTRY,
    build_entitlements,
    can_access_module,
    normalize_plan,
    plan_allows,
    resolve_effective_plan,
)
from product.asset_limits import count_user_assets


router = APIRouter()
_product_schema_ready = False

MISSION_VERIFY_SPECS = {
    "complete_finance": {"xp": 100, "validation": "finance_count > 0"},
    "add_first_asset": {"xp": 120, "validation": "portfolio_count > 0"},
    "diversify_three_assets": {"xp": 90, "validation": "portfolio_count >= 3"},
    "unlock_growth": {"xp": 0, "validation": "plan >= GOLD"},
    "unlock_wealth_os": {"xp": 0, "validation": "plan >= ELITE"},
    "unlock_liberty": {"xp": 0, "validation": "plan >= LIBERTY"},
    "unlock_legacy": {"xp": 0, "validation": "plan >= LEGACY"},
}


def ensure_product_tables(conn):
    global _product_schema_ready

    if _product_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS progression_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            xp INTEGER NOT NULL DEFAULT 0,
            level_name TEXT NOT NULL DEFAULT 'Builder',
            status TEXT NOT NULL DEFAULT 'Foundation',
            streak INTEGER NOT NULL DEFAULT 0,
            last_seen_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS xp_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_module_states (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            module_key TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'locked',
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS user_module_states_unique
        ON user_module_states(user_id, module_key)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS product_mission_completions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            mission_key TEXT NOT NULL,
            xp_awarded INTEGER NOT NULL DEFAULT 0,
            completed_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS product_mission_completions_unique
        ON product_mission_completions(user_id, mission_key)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            action_label TEXT,
            action_url TEXT,
            status TEXT NOT NULL DEFAULT 'unread',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_founder BOOLEAN DEFAULT FALSE"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS founder_tier TEXT"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS founder_discount INTEGER DEFAULT 0"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS level TEXT DEFAULT 'BEGINNER'"))

    _product_schema_ready = True


def safe_count(conn, query: str, params: dict):
    try:
        return int(conn.execute(text(query), params).scalar() or 0)
    except Exception:
        return 0


def safe_float(conn, query: str, params: dict):
    try:
        return float(conn.execute(text(query), params).scalar() or 0)
    except Exception:
        return 0.0


def get_score(email: str) -> int:
    try:
        result = compute_user_intelligence(email) or {}
        return int(result.get("global_score") or result.get("score") or 0)
    except Exception:
        return 0


def compute_level(score: int, xp: int):
    if xp >= 9000:
        return "Dynasty Architect"
    if xp >= 6500:
        return "Legacy Builder"
    if xp >= 5000:
        return "Family Office Operator"
    if xp >= 3000:
        return "Elite Investor"
    if xp >= 1800:
        return "Investor"
    if xp >= 900:
        return "Advanced"
    if xp >= 300:
        return "Builder"
    return "Beginner"


def compute_status(score: int, plan: str):
    if plan_allows(plan, "LEGACY"):
        return "Dynasty Office"
    if plan_allows(plan, "LIBERTY"):
        return "Sovereign Wealth"
    if plan_allows(plan, "ELITE"):
        return "Wealth OS"
    if plan_allows(plan, "GOLD"):
        return "Growth"
    return "Foundation"


def get_next_plan(plan: str):
    normalized = normalize_plan(plan)
    if not plan_allows(normalized, "GOLD"):
        return "gold"
    if not plan_allows(normalized, "ELITE"):
        return "elite"
    if not plan_allows(normalized, "LIBERTY"):
        return "liberty"
    if not plan_allows(normalized, "LEGACY"):
        return "legacy"
    return None


def build_progression(conn, user_id: int, score: int, plan: str):
    ensure_product_tables(conn)

    row = conn.execute(text("""
        SELECT xp, streak
        FROM progression_profiles
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    if not row:
        conn.execute(text("""
            INSERT INTO progression_profiles (user_id, xp, level_name, status)
            VALUES (:user_id, 0, 'Beginner', 'Foundation')
            ON CONFLICT (user_id) DO NOTHING
        """), {"user_id": user_id})
        xp = 0
        streak = 0
    else:
        xp = int(row.xp or 0)
        streak = int(row.streak or 0)

    level_name = compute_level(score, xp)
    status = compute_status(score, plan)
    next_threshold = 1000 * (int(xp / 1000) + 1)

    conn.execute(text("""
        UPDATE progression_profiles
        SET level_name = :level_name,
            status = :status,
            last_seen_at = NOW(),
            updated_at = NOW()
        WHERE user_id = :user_id
    """), {
        "user_id": user_id,
        "level_name": level_name,
        "status": status,
    })

    return {
        "xp": xp,
        "streak": streak,
        "level": level_name,
        "status": status,
        "next_level_xp": next_threshold,
        "progress_percent": min(100, round((xp / next_threshold) * 100, 1)) if next_threshold else 0,
    }


def build_data_profile(conn, user_id: int):
    finance_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM finance_items WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    portfolio_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM portfolio WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    real_estate_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM real_estate_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    yield_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM yield_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    venture_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM venture_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    total_assets_count = count_user_assets(conn, user_id)
    finance_income = safe_float(
        conn,
        "SELECT COALESCE(SUM(amount), 0) FROM finance_items WHERE user_id = :user_id AND type = 'revenus'",
        {"user_id": user_id},
    )
    finance_expenses = safe_float(
        conn,
        "SELECT COALESCE(SUM(amount), 0) FROM finance_items WHERE user_id = :user_id AND type = 'charges'",
        {"user_id": user_id},
    )
    finance_savings = safe_float(
        conn,
        "SELECT COALESCE(SUM(amount), 0) FROM finance_items WHERE user_id = :user_id AND type = 'epargne'",
        {"user_id": user_id},
    )
    finance_debt = safe_float(
        conn,
        "SELECT COALESCE(SUM(amount), 0) FROM finance_items WHERE user_id = :user_id AND type = 'dettes'",
        {"user_id": user_id},
    )
    onboarding_income = safe_float(
        conn,
        "SELECT COALESCE(revenus_mensuels, 0) FROM users WHERE id = :user_id",
        {"user_id": user_id},
    )
    onboarding_expenses = safe_float(
        conn,
        "SELECT COALESCE(charges_mensuelles, 0) FROM users WHERE id = :user_id",
        {"user_id": user_id},
    )
    monthly_income = finance_income or onboarding_income
    monthly_expenses = finance_expenses or onboarding_expenses
    monthly_capacity = max(finance_savings, monthly_income - monthly_expenses, 0)
    portfolio_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(quantity, 0) * COALESCE(purchase_price, 0)), 0)
        FROM portfolio
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    real_estate_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(NULLIF(estimated_value, 0), NULLIF(resale_price, 0), purchase_price, 0)), 0)
        FROM real_estate_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    yield_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(principal, 0) * (1 + (COALESCE(average_rate, 0) / 100) * (COALESCE(duration_months, 12) / 12.0))), 0)
        FROM yield_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    venture_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(
            CASE
                WHEN COALESCE(valuation, 0) > 0 THEN valuation
                ELSE GREATEST(COALESCE(revenue, 0) - COALESCE(charges, 0), 0)
                    + COALESCE(fundraising, 0)
                    - COALESCE(debts, 0)
            END
        ), 0)
        FROM venture_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    business_value = yield_value + venture_value
    current_wealth = portfolio_value + real_estate_value + business_value

    completed_steps = sum([
        finance_count > 0,
        portfolio_count > 0,
        real_estate_count > 0,
        yield_count > 0,
        venture_count > 0,
    ])

    return {
        "finance_count": finance_count,
        "portfolio_count": portfolio_count,
        "real_estate_count": real_estate_count,
        "yield_count": yield_count,
        "venture_count": venture_count,
        "total_assets_count": total_assets_count,
        "completed_steps": completed_steps,
        "completion_percent": round((completed_steps / 5) * 100),
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses": round(monthly_expenses, 2),
        "monthly_savings": round(finance_savings, 2),
        "monthly_capacity": round(monthly_capacity, 2),
        "debt_total": round(finance_debt, 2),
        "portfolio_value": round(portfolio_value, 2),
        "real_estate_value": round(real_estate_value, 2),
        "yield_value": round(yield_value, 2),
        "venture_value": round(venture_value, 2),
        "business_value": round(business_value, 2),
        "current_wealth": round(current_wealth, 2),
    }


def build_modules(plan: str, score: int):
    visible = []

    for module in MODULE_REGISTRY:
        item = {
            **module,
            "required_plan": module["min_plan"],
            "required_score": module["min_score"],
        }

        if can_access_module(plan, score, module):
            visible.append({**item, "state": "active"})
        else:
            visible.append({
                **item,
                "state": "discovery",
                "reason": (
                    "Profondeur limitee sur ton plan actuel"
                    if not plan_allows(plan, module["min_plan"])
                    else "Contexte supplementaire requis pour les analyses avancees"
                ),
            })

    return {"visible": visible, "locked": []}


def mission_completed(mission: dict, data_profile: dict, plan: str) -> bool:
    key = mission.get("key")
    normalized = normalize_plan(plan)

    if key == "complete_finance":
        return data_profile.get("finance_count", 0) > 0
    if key == "add_first_asset":
        return data_profile.get("portfolio_count", 0) > 0
    if key == "diversify_three_assets":
        return data_profile.get("portfolio_count", 0) >= 3
    if key == "unlock_growth":
        return plan_allows(normalized, "GOLD")
    if key == "unlock_wealth_os":
        return plan_allows(normalized, "ELITE")
    if key == "unlock_liberty":
        return plan_allows(normalized, "LIBERTY")
    if key == "unlock_legacy":
        return plan_allows(normalized, "LEGACY")

    return False


def build_missions(data_profile: dict, score: int, plan: str):
    missions = []

    if data_profile["finance_count"] == 0:
        missions.append({
            "key": "complete_finance",
            "title": "Completer les donnees finances",
            "description": "Ajoute au moins un revenu et une charge pour enrichir le contexte financier.",
            "xp": 100,
            "module": "finance",
            "validation": "finance_count > 0",
            "context_reason": "Cette mission alimente le contexte backend.",
        })

    if data_profile["portfolio_count"] == 0:
        missions.append({
            "key": "add_first_asset",
            "title": "Ajouter ton premier actif",
            "description": "Ajoute une action, un ETF, une crypto, une devise ou une commodity avec quantite et prix d'achat.",
            "xp": 120,
            "module": "portfolio",
            "validation": "portfolio_count > 0",
            "context_reason": "Cette mission rend le portefeuille lisible par le backend.",
        })

    if data_profile["portfolio_count"] > 0 and data_profile["portfolio_count"] < 3:
        missions.append({
            "key": "diversify_three_assets",
            "title": "Atteindre trois lignes suivies",
            "description": "Ajoute jusqu'a trois actifs distincts pour rendre la lecture de concentration mesurable.",
            "xp": 90,
            "module": "portfolio",
            "validation": "portfolio_count >= 3",
            "context_reason": "Cette mission donne plus de matiere au suivi de progression.",
        })

    visible_missions = []
    for mission in missions:
        visible_missions.append({
            **mission,
            "completed": mission_completed(mission, data_profile, plan),
        })

    return visible_missions[:3]


def annotate_mission_statuses(conn, user_id: int, missions: list[dict]):
    ensure_product_tables(conn)
    rows = conn.execute(text("""
        SELECT mission_key
        FROM product_mission_completions
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchall()
    verified_keys = {row.mission_key for row in rows}

    annotated = []
    for mission in missions:
        key = mission.get("key")
        if key in verified_keys:
            status = "verified"
        elif mission.get("completed"):
            status = "completed"
        else:
            status = "pending"
        annotated.append({**mission, "status": status})

    return annotated


def build_life_profile(conn, user_id: int):
    try:
        row = conn.execute(text("""
            SELECT goals, investor_profile, motivation, has_children,
                   transmission_goal, governance_need
            FROM user_wealth_profiles
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()
    except Exception:
        row = None

    if not row:
        return {
            "goals": [],
            "professional_context": None,
            "motivation": None,
            "has_children": False,
        }

    return {
        "goals": [item for item in (row.goals or "").split("|") if item],
        "professional_context": row.investor_profile,
        "motivation": row.motivation,
        "has_children": bool(row.has_children),
        "transmission_goal": row.transmission_goal,
        "governance_need": row.governance_need,
    }


def build_strategic_brief(data_profile: dict, score: int, plan: str, life_profile: dict | None = None):
    normalized = normalize_plan(plan)
    life_profile = life_profile or {}
    portfolio_count = data_profile.get("portfolio_count", 0)
    finance_count = data_profile.get("finance_count", 0)
    total_assets = data_profile.get("total_assets_count", 0)
    goals_text = " ".join(life_profile.get("goals") or [])
    motivation = str(life_profile.get("motivation") or "")
    wants_income = "revenu" in goals_text.lower() or "revenu" in motivation.lower() or "liberte" in motivation.lower()
    has_children = bool(life_profile.get("has_children"))
    professional = str(life_profile.get("professional_context") or "")

    if wants_income and ("marketing" in professional.lower() or data_profile.get("venture_count", 0) > 0):
        priority = "Monetiser une competence deja presente"
        action = "Donnee contextuelle: competence business existante et temps limite."
    elif has_children and plan_allows(normalized, "LIBERTY"):
        priority = "Relier patrimoine et protection familiale"
        action = "Donnee contextuelle: famille et transmission disponibles dans le profil."
    elif finance_count == 0:
        priority = "Completer le contexte financier"
        action = "Donnee manquante: revenu ou charge a renseigner."
    elif portfolio_count == 0:
        priority = "Créer la premiere ligne patrimoniale mesurable"
        action = "Donnee manquante: actif financier a renseigner."
    else:
        priority = "Qualifier le prochain signal utile"
        action = "Signal disponible: objectifs, temps et risque peuvent etre compares par le moteur central."

    if plan_allows(normalized, "LEGACY"):
        opportunity = "Signal familial: gouvernance ou transmission renseignee."
        risk = "Signal de vigilance: roles familiaux incomplets."
    elif plan_allows(normalized, "LIBERTY"):
        opportunity = "Signal de profondeur: scenario 12 mois disponible."
        risk = "Signal de vigilance: intention patrimoniale a expliciter."
    elif plan_allows(normalized, "GOLD"):
        opportunity = "Signal produit: contexte portefeuille et objectifs disponibles pour le moteur central."
        risk = "Signal de vigilance: concentration a mesurer."
    else:
        opportunity = "Signal produit: base de donnees a enrichir."
        risk = "Signal de vigilance: contexte encore incomplet."

    return {
        "priority": priority,
        "main_lever": f"{total_assets} asset(s) suivis, {data_profile.get('completion_percent', 0)}% de completion.",
        "main_risk": risk,
        "opportunity": opportunity,
        "next_action": action,
        "context_basis": {
            "goals": life_profile.get("goals") or [],
            "has_children": has_children,
            "professional_context": life_profile.get("professional_context"),
        },
    }


def build_future_view(data_profile: dict, score: int, plan: str):
    normalized = normalize_plan(plan)
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)

    if plan_allows(normalized, "LIBERTY"):
        annual_return = 0.055
    elif plan_allows(normalized, "GOLD"):
        annual_return = 0.045
    else:
        annual_return = 0.035

    if score >= 70:
        annual_return += 0.005
    elif score < 35:
        annual_return -= 0.005

    annual_contribution = max(monthly_capacity, 0) * 12

    def project(years: int):
        value = current_wealth
        for _ in range(years):
            value = value * (1 + annual_return) + annual_contribution
        return round(value, 2)

    if current_wealth > 0 and monthly_capacity > 0:
        confidence = "solid"
        assumption = "Projection backend: patrimoine actuel, capacite mensuelle declaree et rendement prudent."
    elif current_wealth > 0:
        confidence = "asset_based"
        assumption = "Projection backend: patrimoine actuel uniquement, sans capacite mensuelle exploitable."
    else:
        confidence = "data_light"
        assumption = "Projection backend limitee: ajoute revenus, charges et actifs pour rendre le futur lisible."

    return {
        "title": "Future View",
        "current_wealth": round(current_wealth, 2),
        "monthly_capacity": round(monthly_capacity, 2),
        "annual_return": round(annual_return * 100, 2),
        "confidence": confidence,
        "assumption": assumption,
        "scenarios": [
            {"label": "3 ans", "years": 3, "value": project(3)},
            {"label": "5 ans", "years": 5, "value": project(5)},
            {"label": "10 ans", "years": 10, "value": project(10)},
        ],
    }


def build_wealth_timeline(data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    stages = [
        ("Aujourd'hui", 0),
        ("100k", 100000),
        ("250k", 250000),
        ("500k", 500000),
        ("1M", 1000000),
        ("Liberte financiere", 1500000),
    ]
    timeline = []
    next_stage = None

    for label, target in stages:
        if target == 0:
            status = "current"
            progress = 100
        else:
            status = "achieved" if current_wealth >= target else "locked"
            progress = min(100, round((current_wealth / target) * 100, 1)) if target else 100
            if status == "locked" and next_stage is None:
                next_stage = {"label": label, "target": target}

        timeline.append({
            "label": label,
            "target": target,
            "status": status,
            "progress_percent": progress,
        })

    return {
        "current_wealth": round(current_wealth, 2),
        "progress_percent": min(100, round((current_wealth / 1000000) * 100, 1)) if current_wealth else 0,
        "next_milestone": next_stage,
        "stages": timeline,
    }


def build_mission_control(strategic_brief: dict, missions: list[dict], data_profile: dict, future_view: dict):
    mission = next((item for item in missions if item.get("status") != "verified"), None)
    if not mission and missions:
        mission = missions[0]

    return {
        "risk": {
            "title": "Risque principal",
            "description": strategic_brief.get("main_risk"),
        },
        "opportunity": {
            "title": "Opportunite",
            "description": strategic_brief.get("opportunity"),
        },
        "decision": {
            "title": "Decision du moment",
            "description": strategic_brief.get("priority"),
            "action": strategic_brief.get("next_action"),
        },
        "mission": {
            "title": mission.get("title") if mission else "Contexte a enrichir",
            "description": mission.get("description") if mission else "Ajoute une donnee utile pour activer une mission verifiable.",
            "status": mission.get("status") if mission else "pending",
            "xp": mission.get("xp") if mission else 0,
        },
        "future_signal": {
            "title": "Projection",
            "description": future_view.get("assumption"),
            "confidence": future_view.get("confidence"),
        },
    }


def build_family_office_view(data_profile: dict, plan: str):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    allocation = [
        {
            "key": "investments",
            "label": "Investissements",
            "value": round(float(data_profile.get("portfolio_value") or 0), 2),
            "description": "Actifs financiers suivis par le portefeuille backend.",
        },
        {
            "key": "real_estate",
            "label": "Immobilier",
            "value": round(float(data_profile.get("real_estate_value") or 0), 2),
            "description": "Valeur estimee des biens immobiliers suivis.",
        },
        {
            "key": "business",
            "label": "Business",
            "value": round(float(data_profile.get("business_value") or 0), 2),
            "description": "Yield assets, private equity et activites valorisees.",
        },
    ]

    active_domains = sum(1 for item in allocation if item["value"] > 0)
    if current_wealth > 0:
        summary = "Lecture globale active: le patrimoine est consolide par domaines."
    else:
        summary = "Lecture globale prete: ajoute actifs, immobilier ou business pour activer la valeur."

    return {
        "title": "Family Office Mode",
        "summary": summary,
        "global_wealth": round(current_wealth, 2),
        "active_domains": active_domains,
        "plan": normalize_plan(plan),
        "allocation": allocation,
    }


def build_wealth_gps(data_profile: dict, future_view: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    next_milestone = next(
        (item for item in [100000, 250000, 500000, 1000000] if current_wealth < item),
        1500000,
    )

    routes = [
        {
            "key": "markets",
            "label": "Marches financiers",
            "annual_return": 0.055,
            "monthly_multiplier": 1,
            "description": "Trajectoire liquide basee sur la capacite mensuelle et le portefeuille financier.",
        },
        {
            "key": "real_estate",
            "label": "Immobilier",
            "annual_return": 0.045,
            "monthly_multiplier": 1.1,
            "description": "Trajectoire patrimoniale avec effet capital long terme et effort d'epargne plus structure.",
        },
        {
            "key": "business",
            "label": "Business",
            "annual_return": 0.075,
            "monthly_multiplier": 1.2,
            "description": "Trajectoire orientee creation de valeur via activite, expertise ou revenus semi-recurrents.",
        },
        {
            "key": "balanced",
            "label": "Mix equilibre",
            "annual_return": 0.06,
            "monthly_multiplier": 1.05,
            "description": "Trajectoire hybride entre liquidite, croissance et diversification progressive.",
        },
    ]

    def project_route(route: dict, years: int):
        value = current_wealth
        annual_contribution = monthly_capacity * float(route["monthly_multiplier"]) * 12
        for _ in range(years):
            value = value * (1 + float(route["annual_return"])) + annual_contribution
        return round(value, 2)

    enriched_routes = []
    for route in routes:
        value_10y = project_route(route, 10)
        years_to_next = None
        if next_milestone > current_wealth:
            value = current_wealth
            annual_contribution = monthly_capacity * float(route["monthly_multiplier"]) * 12
            for year in range(1, 31):
                value = value * (1 + float(route["annual_return"])) + annual_contribution
                if value >= next_milestone:
                    years_to_next = year
                    break

        enriched_routes.append({
            **route,
            "annual_return": round(float(route["annual_return"]) * 100, 2),
            "value_10y": value_10y,
            "years_to_next_milestone": years_to_next,
        })

    return {
        "title": "GPS patrimonial",
        "current_position": round(current_wealth, 2),
        "next_destination": next_milestone,
        "assumption": future_view.get("assumption"),
        "routes": enriched_routes,
    }


def build_digital_twin(data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    base_monthly = monthly_capacity if monthly_capacity > 0 else 0
    scenarios = [
        {
            "key": "invest_500",
            "label": "Investir 500 EUR/mois",
            "monthly_delta": 500,
            "annual_return": 0.055,
            "description": "Simulation d'une discipline d'investissement mensuelle fixe.",
        },
        {
            "key": "business_plus",
            "label": "Developper un revenu business",
            "monthly_delta": 750,
            "annual_return": 0.06,
            "description": "Simulation d'un surplus mensuel cree par activite ou offre recurrente.",
        },
        {
            "key": "keep_current",
            "label": "Continuer au rythme actuel",
            "monthly_delta": 0,
            "annual_return": 0.045,
            "description": "Simulation de reference avec les donnees deja presentes dans le backend.",
        },
    ]

    def simulate(monthly_delta: float, annual_return: float, years: int):
        value = current_wealth
        annual_contribution = max(base_monthly + monthly_delta, 0) * 12
        for _ in range(years):
            value = value * (1 + annual_return) + annual_contribution
        return round(value, 2)

    return {
        "title": "Double patrimonial",
        "basis": "Simulations backend hypothetiques, sans remplacer Ethan ni une decision personnelle.",
        "scenarios": [
            {
                **scenario,
                "annual_return": round(float(scenario["annual_return"]) * 100, 2),
                "value_5y": simulate(float(scenario["monthly_delta"]), float(scenario["annual_return"]), 5),
                "value_10y": simulate(float(scenario["monthly_delta"]), float(scenario["annual_return"]), 10),
            }
            for scenario in scenarios
        ],
    }


def build_weak_signals(data_profile: dict, life_profile: dict | None = None):
    life_profile = life_profile or {}
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    allocation = {
        "investments": float(data_profile.get("portfolio_value") or 0),
        "real_estate": float(data_profile.get("real_estate_value") or 0),
        "business": float(data_profile.get("business_value") or 0),
    }
    signals = []

    if data_profile.get("completion_percent", 0) < 60:
        signals.append({
            "type": "data_depth",
            "title": "Contexte incomplet",
            "description": "Le cockpit manque encore de donnees pour lire toute la trajectoire.",
            "severity": "medium",
        })

    if monthly_capacity <= 0 and (data_profile.get("monthly_income", 0) or data_profile.get("monthly_expenses", 0)):
        signals.append({
            "type": "capacity",
            "title": "Capacite mensuelle fragile",
            "description": "Les donnees backend ne montrent pas encore de marge mensuelle exploitable.",
            "severity": "high",
        })

    if current_wealth > 0:
        main_domain, main_value = max(allocation.items(), key=lambda item: item[1])
        if main_value / current_wealth >= 0.7:
            labels = {"investments": "investissements", "real_estate": "immobilier", "business": "business"}
            signals.append({
                "type": "concentration",
                "title": "Concentration patrimoniale",
                "description": f"Le domaine {labels.get(main_domain, main_domain)} porte une grande partie de la valeur suivie.",
                "severity": "medium",
            })

    if life_profile.get("has_children") and current_wealth > 0:
        signals.append({
            "type": "family",
            "title": "Protection familiale a anticiper",
            "description": "La presence d'enfants rend la trajectoire patrimoniale plus sensible a la protection et la transmission.",
            "severity": "medium",
        })

    if not signals:
        signals.append({
            "type": "stability",
            "title": "Aucun signal critique",
            "description": "Les donnees disponibles ne font pas ressortir de fragilite immediate.",
            "severity": "low",
        })

    return {
        "title": "Signaux faibles",
        "signals": signals[:4],
    }


def build_self_benchmark(conn, user_id: int, data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    value_6m = safe_float(
        conn,
        """
        SELECT total_value
        FROM portfolio_history
        WHERE user_id = :user_id AND created_at <= NOW() - INTERVAL '6 months'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"user_id": user_id},
    )
    value_12m = safe_float(
        conn,
        """
        SELECT total_value
        FROM portfolio_history
        WHERE user_id = :user_id AND created_at <= NOW() - INTERVAL '12 months'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"user_id": user_id},
    )

    def delta(previous: float):
        if previous <= 0:
            return None
        return {
            "previous_value": round(previous, 2),
            "delta_value": round(current_wealth - previous, 2),
            "delta_percent": round(((current_wealth - previous) / previous) * 100, 1),
        }

    return {
        "title": "Classement contre toi-meme",
        "current_wealth": round(current_wealth, 2),
        "six_months": delta(value_6m),
        "twelve_months": delta(value_12m),
        "basis": "Comparaison backend avec l'historique portfolio disponible.",
    }


def build_wealth_story(data_profile: dict, progression: dict):
    events = [
        {
            "label": "Aujourd'hui",
            "title": "Point de depart patrimonial",
            "description": f"{round(float(data_profile.get('current_wealth') or 0), 2)} EUR suivis dans White Rock.",
        },
        {
            "label": "Progression",
            "title": progression.get("level") or "Builder",
            "description": f"{progression.get('xp', 0)} XP et {data_profile.get('completion_percent', 0)}% de contexte complete.",
        },
    ]

    if data_profile.get("portfolio_count", 0) > 0:
        events.append({
            "label": "Investissements",
            "title": "Portefeuille active",
            "description": f"{data_profile.get('portfolio_count', 0)} ligne(s) financiere(s) suivie(s).",
        })
    if data_profile.get("real_estate_count", 0) > 0:
        events.append({
            "label": "Immobilier",
            "title": "Brique immobiliere",
            "description": f"{data_profile.get('real_estate_count', 0)} bien(s) integre(s) au patrimoine global.",
        })
    if data_profile.get("business_value", 0) > 0:
        events.append({
            "label": "Business",
            "title": "Valeur entrepreneuriale",
            "description": "Une valeur business est maintenant visible dans la carte patrimoniale.",
        })

    return {
        "title": "Histoire de ta richesse",
        "events": events,
    }


def build_opportunity_radar(data_profile: dict, life_profile: dict | None = None):
    life_profile = life_profile or {}
    professional = str(life_profile.get("professional_context") or "").lower()
    goals_text = " ".join(life_profile.get("goals") or []).lower()
    motivation = str(life_profile.get("motivation") or "").lower()
    wants_income = any(word in f"{goals_text} {motivation}" for word in ["revenu", "liberte", "business"])
    marketing_fit = any(word in professional for word in ["marketing", "communication", "commerce", "business"])
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)

    opportunities = []
    if marketing_fit or wants_income:
        opportunities.append({
            "key": "marketing_recurring_offer",
            "title": "Offre recurrente marketing",
            "why_fit": "Compatible avec une expertise existante et une contrainte de temps forte.",
            "time_fit": "Court si l'offre est standardisee.",
            "impact": "Peut augmenter les revenus sans creer un nouveau chantier lourd.",
            "next_action": "Formaliser une offre simple, un prix fixe et une cible precise.",
            "priority": "high",
        })
        opportunities.append({
            "key": "digital_product",
            "title": "Produit numerique issu de l'expertise",
            "why_fit": "Transforme une competence deja presente en actif reutilisable.",
            "time_fit": "Moyen: utile seulement si le format reste tres simple.",
            "impact": "Potentiel de revenu scalable, mais validation commerciale indispensable.",
            "next_action": "Identifier une douleur client repetitive et une promesse vendable.",
            "priority": "medium",
        })

    if monthly_capacity > 0:
        opportunities.append({
            "key": "automated_investing",
            "title": "Investissement mensuel automatise",
            "why_fit": "La capacite mensuelle existe dans les donnees backend.",
            "time_fit": "Faible charge mentale si la regle est simple.",
            "impact": "Construit une trajectoire patrimoniale sans multiplier les decisions.",
            "next_action": "Fixer un montant prudent et une frequence automatique.",
            "priority": "medium",
        })

    opportunities.append({
        "key": "small_business_acquisition",
        "title": "Acquisition d'un petit actif digital",
        "why_fit": "Interessant si le business complete les competences existantes.",
        "time_fit": "A filtrer strictement: beaucoup d'opportunites sont incompatibles avec peu de temps.",
        "impact": "Peut creer un levier, mais uniquement avec operations simples.",
        "next_action": "Lister les criteres d'exclusion avant de regarder des deals.",
        "priority": "low",
    })

    return {
        "title": "Radar d'opportunites",
        "principle": "Les opportunites sont filtrees par coherence avec la situation, pas par popularite.",
        "items": opportunities[:3],
    }


def build_decision_engine(data_profile: dict):
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    current_wealth = float(data_profile.get("current_wealth") or 0)
    business_value = float(data_profile.get("business_value") or 0)

    return {
        "title": "Moteur de decisions",
        "decisions": [
            {
                "key": "develop_business",
                "label": "Developper l'activite",
                "cashflow": "+",
                "liquidity": "+",
                "risk": "moyen",
                "freedom_impact": "+++",
                "fit": "fort" if business_value > 0 or monthly_capacity <= 1000 else "moyen",
                "comment": "Levier prioritaire si l'objectif est d'augmenter les revenus avec une competence existante.",
            },
            {
                "key": "buy_real_estate",
                "label": "Acheter un bien immobilier",
                "cashflow": "+/-",
                "liquidity": "-",
                "risk": "moyen",
                "freedom_impact": "++",
                "fit": "moyen" if monthly_capacity > 0 else "faible",
                "comment": "Decision pertinente seulement si la marge mensuelle et la reserve de securite sont suffisantes.",
            },
            {
                "key": "invest_monthly",
                "label": "Investir chaque mois",
                "cashflow": "-",
                "liquidity": "+/-",
                "risk": "modere",
                "freedom_impact": "++",
                "fit": "fort" if monthly_capacity > 0 else "faible",
                "comment": "Decision robuste quand elle reste automatique et proportionnee a la capacite disponible.",
            },
            {
                "key": "balanced_path",
                "label": "Mixer business + investissement",
                "cashflow": "+",
                "liquidity": "+/-",
                "risk": "moyen",
                "freedom_impact": "+++",
                "fit": "fort" if current_wealth > 0 and monthly_capacity > 0 else "moyen",
                "comment": "Chemin coherent si l'utilisateur veut croissance sans dependance a un seul levier.",
            },
        ],
    }


def build_time_value(data_profile: dict):
    monthly_income = float(data_profile.get("monthly_income") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    hourly_value = round(monthly_income / 151.67, 2) if monthly_income > 0 else 0

    return {
        "title": "Valeur du temps",
        "hourly_value": hourly_value,
        "monthly_capacity": round(monthly_capacity, 2),
        "basis": "Estimation backend basee sur le revenu mensuel et un temps plein standard.",
        "levers": [
            {
                "label": "Prestation sur mesure",
                "time_cost": "eleve",
                "leverage": "faible a moyen",
                "reading": "A limiter si le temps familial est rare.",
            },
            {
                "label": "Offre packagée",
                "time_cost": "moyen",
                "leverage": "fort",
                "reading": "Meilleur rapport temps/revenu si la promesse est claire.",
            },
            {
                "label": "Produit digital",
                "time_cost": "initial eleve",
                "leverage": "fort apres validation",
                "reading": "Interessant seulement apres preuve de demande.",
            },
        ],
    }


def build_wealth_blocks(data_profile: dict):
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    debt_total = float(data_profile.get("debt_total") or 0)

    return {
        "title": "Construction par blocs",
        "blocks": [
            {
                "key": "security",
                "label": "Bloc securite",
                "value": max(monthly_capacity * 3, 0),
                "status": "active" if monthly_capacity > 0 else "to_build",
                "description": "Reserve et marge mensuelle disponibles.",
            },
            {
                "key": "income",
                "label": "Bloc revenus",
                "value": float(data_profile.get("monthly_income") or 0),
                "status": "active" if data_profile.get("monthly_income", 0) else "to_build",
                "description": "Base de revenus suivie par le backend.",
            },
            {
                "key": "markets",
                "label": "Bloc marches financiers",
                "value": float(data_profile.get("portfolio_value") or 0),
                "status": "active" if data_profile.get("portfolio_value", 0) else "to_build",
                "description": "Actifs financiers liquides.",
            },
            {
                "key": "real_estate",
                "label": "Bloc immobilier",
                "value": float(data_profile.get("real_estate_value") or 0),
                "status": "active" if data_profile.get("real_estate_value", 0) else "to_build",
                "description": "Actifs immobiliers et valeur estimee.",
            },
            {
                "key": "business",
                "label": "Bloc business",
                "value": float(data_profile.get("business_value") or 0),
                "status": "active" if data_profile.get("business_value", 0) else "to_build",
                "description": "Valeur entrepreneuriale, yield assets et ventures.",
            },
            {
                "key": "debt",
                "label": "Bloc dette",
                "value": debt_total,
                "status": "watch" if debt_total > 0 else "clear",
                "description": "Dette suivie dans les finances.",
            },
        ],
    }


def build_dependency_detector(data_profile: dict, life_profile: dict | None = None):
    life_profile = life_profile or {}
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_income = float(data_profile.get("monthly_income") or 0)
    business_value = float(data_profile.get("business_value") or 0)
    signals = []

    if monthly_income > 0 and business_value <= 0:
        signals.append({
            "type": "income_source",
            "title": "Dependance au revenu actif",
            "description": "Le backend voit un revenu mensuel mais pas encore de bloc business valorise.",
            "severity": "medium",
        })
    if data_profile.get("portfolio_count", 0) <= 1 and current_wealth > 0:
        signals.append({
            "type": "asset_concentration",
            "title": "Dependance a peu d'actifs",
            "description": "Le patrimoine suivi repose sur peu de lignes mesurables.",
            "severity": "medium",
        })
    if life_profile.get("has_children") and monthly_income > 0:
        signals.append({
            "type": "family_income",
            "title": "Dependance familiale au revenu courant",
            "description": "La charge familiale rend l'interruption de revenus plus sensible.",
            "severity": "high",
        })
    if not signals:
        signals.append({
            "type": "balanced",
            "title": "Aucune dependance majeure detectee",
            "description": "Les donnees backend ne montrent pas encore de fragilite de dependance dominante.",
            "severity": "low",
        })

    return {
        "title": "Detecteur de dependances",
        "signals": signals[:3],
    }


def build_personal_command_center(
    mission_control: dict,
    opportunity_radar: dict,
    dependency_detector: dict,
    time_value: dict,
):
    radar_items = opportunity_radar.get("items") or []
    dependencies = dependency_detector.get("signals") or []

    return {
        "title": "Centre de commandement personnel",
        "situation": mission_control.get("decision", {}).get("description"),
        "threat": dependencies[0] if dependencies else None,
        "opportunity": radar_items[0] if radar_items else mission_control.get("opportunity"),
        "mission": mission_control.get("mission"),
        "next_step": (
            radar_items[0].get("next_action")
            if radar_items
            else mission_control.get("decision", {}).get("action")
        ),
        "time_value": time_value,
    }


@router.get("/entitlements")
def product_entitlements(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        plan_row = conn.execute(text("""
            SELECT
                users.plan AS user_plan,
                users.is_founder,
                users.founder_tier,
                users.founder_discount,
                subscriptions.plan AS subscription_plan,
                subscriptions.status AS subscription_status
            FROM users
            LEFT JOIN subscriptions ON subscriptions.user_id = users.id
            WHERE users.id = :user_id
        """), {"user_id": user_id}).fetchone()

        plan = resolve_effective_plan(
            plan_row.user_plan if plan_row else "FREE",
            plan_row.subscription_plan if plan_row else None,
            plan_row.subscription_status if plan_row else None,
        )

    return {
        "plan": plan,
        "entitlements": build_entitlements(plan),
        "founder": {
            "is_founder": bool(plan_row.is_founder) if plan_row else False,
            "tier": plan_row.founder_tier if plan_row else None,
            "discount": int(plan_row.founder_discount or 0) if plan_row else 0,
        },
    }


@router.get("/context")
def product_context(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        plan_row = conn.execute(text("""
            SELECT
                users.plan AS user_plan,
                users.is_founder,
                users.founder_tier,
                users.founder_discount,
                subscriptions.plan AS subscription_plan,
                subscriptions.status AS subscription_status
            FROM users
            LEFT JOIN subscriptions ON subscriptions.user_id = users.id
            WHERE users.id = :user_id
        """), {"user_id": user_id}).fetchone()

        plan = resolve_effective_plan(
            plan_row.user_plan if plan_row else "FREE",
            plan_row.subscription_plan if plan_row else None,
            plan_row.subscription_status if plan_row else None,
        )
        score = get_score(email)
        entitlements = build_entitlements(plan)
        data_profile = build_data_profile(conn, user_id)
        progression = build_progression(conn, user_id, score, plan)
        modules = build_modules(plan, score)
        missions = annotate_mission_statuses(
            conn,
            user_id,
            build_missions(data_profile, score, plan),
        )
        life_profile = build_life_profile(conn, user_id)
        strategic_brief = build_strategic_brief(data_profile, score, plan, life_profile)
        future_view = build_future_view(data_profile, score, plan)
        wealth_timeline = build_wealth_timeline(data_profile)
        mission_control = build_mission_control(strategic_brief, missions, data_profile, future_view)
        family_office_view = build_family_office_view(data_profile, plan)
        wealth_gps = build_wealth_gps(data_profile, future_view)
        digital_twin = build_digital_twin(data_profile)
        weak_signals = build_weak_signals(data_profile, life_profile)
        self_benchmark = build_self_benchmark(conn, user_id, data_profile)
        wealth_story = build_wealth_story(data_profile, progression)
        opportunity_radar = build_opportunity_radar(data_profile, life_profile)
        decision_engine = build_decision_engine(data_profile)
        time_value = build_time_value(data_profile)
        wealth_blocks = build_wealth_blocks(data_profile)
        dependency_detector = build_dependency_detector(data_profile, life_profile)
        personal_command_center = build_personal_command_center(
            mission_control,
            opportunity_radar,
            dependency_detector,
            time_value,
        )

    return {
        "plan": plan,
        "next_plan": get_next_plan(plan),
        "score": score,
        "entitlements": entitlements,
        "progression": progression,
        "data_profile": data_profile,
        "life_profile": life_profile,
        "modules": modules,
        "missions": missions,
        "strategic_brief": strategic_brief,
        "mission_control": mission_control,
        "future_view": future_view,
        "wealth_timeline": wealth_timeline,
        "family_office_view": family_office_view,
        "wealth_gps": wealth_gps,
        "digital_twin": digital_twin,
        "weak_signals": weak_signals,
        "self_benchmark": self_benchmark,
        "wealth_story": wealth_story,
        "opportunity_radar": opportunity_radar,
        "decision_engine": decision_engine,
        "time_value": time_value,
        "wealth_blocks": wealth_blocks,
        "dependency_detector": dependency_detector,
        "personal_command_center": personal_command_center,
        "founder": {
            "is_founder": bool(plan_row.is_founder) if plan_row else False,
            "tier": plan_row.founder_tier if plan_row else None,
            "discount": int(plan_row.founder_discount or 0) if plan_row else 0,
        },
    }


@router.post("/missions/{mission_key}/verify")
def verify_product_mission(mission_key: str, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_product_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        plan_row = conn.execute(text("""
            SELECT
                users.plan AS user_plan,
                subscriptions.plan AS subscription_plan,
                subscriptions.status AS subscription_status
            FROM users
            LEFT JOIN subscriptions ON subscriptions.user_id = users.id
            WHERE users.id = :user_id
        """), {"user_id": user_id}).fetchone()

        plan = resolve_effective_plan(
            plan_row.user_plan if plan_row else "FREE",
            plan_row.subscription_plan if plan_row else None,
            plan_row.subscription_status if plan_row else None,
        )
        score = get_score(email)
        data_profile = build_data_profile(conn, user_id)
        missions = build_missions(data_profile, score, plan)
        mission = next((item for item in missions if item.get("key") == mission_key), None)

        if not mission:
            mission = {"key": mission_key, **MISSION_VERIFY_SPECS.get(mission_key, {})}

        if mission_key not in MISSION_VERIFY_SPECS and not mission.get("validation"):
            raise HTTPException(status_code=404, detail="Mission not found")

        completed = mission_completed(mission, data_profile, plan)
        already = conn.execute(text("""
            SELECT xp_awarded
            FROM product_mission_completions
            WHERE user_id = :user_id AND mission_key = :mission_key
        """), {"user_id": user_id, "mission_key": mission_key}).fetchone()

        xp_awarded = 0
        if completed and not already:
            xp_awarded = int(mission.get("xp") or 0)
            conn.execute(text("""
                INSERT INTO product_mission_completions (user_id, mission_key, xp_awarded)
                VALUES (:user_id, :mission_key, :xp_awarded)
                ON CONFLICT (user_id, mission_key) DO NOTHING
            """), {
                "user_id": user_id,
                "mission_key": mission_key,
                "xp_awarded": xp_awarded,
            })
            if xp_awarded > 0:
                award_xp(conn, user_id, email, f"mission_{mission_key}_completed", xp_awarded)

    return {
        "mission_key": mission_key,
        "completed": completed,
        "status": "verified" if completed else "pending",
        "xp_awarded": xp_awarded,
        "already_completed": bool(already),
        "validation": mission.get("validation"),
    }
