from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from intelligence.user_intelligence_engine import compute_user_intelligence
from product.entitlements import (
    MODULE_REGISTRY,
    build_entitlements,
    can_access_module,
    normalize_plan,
    plan_allows,
    resolve_effective_plan,
)


router = APIRouter()
_product_schema_ready = False


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
    if score >= 95 or xp >= 9000:
        return "Dynasty Architect"
    if score >= 88 or xp >= 6500:
        return "Legacy Builder"
    if score >= 85 or xp >= 5000:
        return "Family Office Operator"
    if score >= 75 or xp >= 3000:
        return "Elite Investor"
    if score >= 60 or xp >= 1800:
        return "Investor"
    if score >= 45 or xp >= 900:
        return "Advanced"
    if score >= 25 or xp >= 300:
        return "Builder"
    return "Beginner"


def compute_status(score: int, plan: str):
    if plan_allows(plan, "LEGACY"):
        return "Dynasty Office"
    if plan_allows(plan, "LIBERTY"):
        return "Sovereign Wealth"
    if plan_allows(plan, "ELITE"):
        return "Wealth OS"
    if score >= 70:
        return "Acceleration"
    if score >= 40:
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
    total_assets_count = portfolio_count + real_estate_count + yield_count + venture_count
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
                    else f"Score {module['min_score']} requis pour les analyses avancees"
                ),
            })

    return {"visible": visible, "locked": []}


def build_missions(data_profile: dict, score: int, plan: str):
    missions = []

    if data_profile["finance_count"] == 0:
        missions.append({
            "key": "complete_finance",
            "title": "Completer ton cashflow",
            "description": "Ajoute revenus, charges, epargne et dettes pour clarifier tes fondations.",
            "xp": 100,
            "module": "finance",
        })

    if data_profile["portfolio_count"] == 0:
        missions.append({
            "key": "add_first_asset",
            "title": "Ajouter ton premier actif",
            "description": "C'est le premier pas vers une vision patrimoniale centralisee.",
            "xp": 120,
            "module": "portfolio",
        })

    if score >= 45 and normalize_plan(plan) == "FREE":
        missions.append({
            "key": "unlock_growth",
            "title": "Debloquer la phase Growth",
            "description": "Ton profil commence a justifier diversification, immobilier et analytics.",
            "xp": 0,
            "module": "billing",
            "recommended_plan": "gold",
        })

    if score >= 70 and not plan_allows(plan, "ELITE"):
        missions.append({
            "key": "unlock_wealth_os",
            "title": "Passer en pilotage Wealth OS",
            "description": "Ton niveau devient compatible avec multi-user, gouvernance et guidance premium.",
            "xp": 0,
            "module": "billing",
            "recommended_plan": "elite",
        })

    if score >= 85 and not plan_allows(plan, "LIBERTY"):
        missions.append({
            "key": "unlock_liberty",
            "title": "Debloquer Liberty",
            "description": "Ton profil devient compatible avec une architecture patrimoniale souveraine.",
            "xp": 0,
            "module": "billing",
            "recommended_plan": "liberty",
        })

    if score >= 92 and not plan_allows(plan, "LEGACY"):
        missions.append({
            "key": "unlock_legacy",
            "title": "Preparer Legacy",
            "description": "Le vrai luxe est la stabilite: transmission, gouvernance et protection familiale.",
            "xp": 0,
            "module": "billing",
            "recommended_plan": "legacy",
        })

    return missions[:3]


def build_strategic_brief(data_profile: dict, score: int, plan: str):
    normalized = normalize_plan(plan)
    portfolio_count = data_profile.get("portfolio_count", 0)
    finance_count = data_profile.get("finance_count", 0)
    total_assets = data_profile.get("total_assets_count", 0)

    if finance_count == 0:
        priority = "Completer le contexte financier"
        action = "Donnee manquante: revenu ou charge a renseigner."
    elif portfolio_count == 0:
        priority = "Creer la premiere ligne patrimoniale mesurable"
        action = "Donnee manquante: actif financier a renseigner."
    elif data_profile.get("monthly_capacity", 0) > 0:
        priority = "Transformer la capacite mensuelle en trajectoire"
        action = "Signal disponible: capacite mensuelle et patrimoine peuvent etre projetes."
    else:
        priority = "Qualifier le prochain signal utile"
        action = "Signal disponible: objectifs, temps et risque peuvent etre compares par Ethan."

    if plan_allows(normalized, "LEGACY"):
        opportunity = "Signal familial: gouvernance ou transmission a structurer."
        risk = "Signal de vigilance: roles familiaux incomplets."
    elif plan_allows(normalized, "LIBERTY"):
        opportunity = "Signal de profondeur: scenario patrimonial 12 mois disponible."
        risk = "Signal de vigilance: intention patrimoniale a expliciter."
    elif plan_allows(normalized, "GOLD"):
        opportunity = "Signal produit: contexte portefeuille et objectifs disponibles pour Ethan."
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


def build_mission_control(strategic_brief: dict, missions: list[dict], future_view: dict):
    mission = next((item for item in missions if not item.get("completed")), None)
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
    summary = (
        "Lecture globale active: le patrimoine est consolide par domaines."
        if current_wealth > 0
        else "Lecture globale prete: ajoute actifs, immobilier ou business pour activer la valeur."
    )

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
            "value_10y": project_route(route, 10),
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
        annual_contribution = max(monthly_capacity + monthly_delta, 0) * 12
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


def build_weak_signals(data_profile: dict):
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
        missions = build_missions(data_profile, score, plan)
        strategic_brief = build_strategic_brief(data_profile, score, plan)
        future_view = build_future_view(data_profile, score, plan)
        wealth_timeline = build_wealth_timeline(data_profile)
        mission_control = build_mission_control(strategic_brief, missions, future_view)
        family_office_view = build_family_office_view(data_profile, plan)
        wealth_gps = build_wealth_gps(data_profile, future_view)
        digital_twin = build_digital_twin(data_profile)
        weak_signals = build_weak_signals(data_profile)
        self_benchmark = build_self_benchmark(conn, user_id, data_profile)
        wealth_story = build_wealth_story(data_profile, progression)

    return {
        "plan": plan,
        "next_plan": get_next_plan(plan),
        "score": score,
        "entitlements": entitlements,
        "progression": progression,
        "data_profile": data_profile,
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
        "founder": {
            "is_founder": bool(plan_row.is_founder) if plan_row else False,
            "tier": plan_row.founder_tier if plan_row else None,
            "discount": int(plan_row.founder_discount or 0) if plan_row else 0,
        },
    }
