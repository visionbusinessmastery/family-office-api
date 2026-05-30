from datetime import date

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
    locked = []

    for module in MODULE_REGISTRY:
        item = {
            **module,
            "required_plan": module["min_plan"],
            "required_score": module["min_score"],
        }

        if can_access_module(plan, score, module):
            visible.append({**item, "state": "active"})
        else:
            locked_item = {
                **item,
                "state": "discovery",
                "reason": (
                    "Profondeur limitee sur ton plan actuel"
                    if not plan_allows(plan, module["min_plan"])
                    else "Contexte supplementaire requis pour les analyses avancees"
                ),
            }
            visible.append(locked_item)
            locked.append(locked_item)

    return {"visible": visible, "locked": locked}


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


MONTH_LABELS = [
    "janvier",
    "fevrier",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "aout",
    "septembre",
    "octobre",
    "novembre",
    "decembre",
]


def add_months(base_date: date, months: int):
    month_index = base_date.month - 1 + max(months, 0)
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def estimate_months_to_target(current_wealth: float, monthly_capacity: float, annual_return: float, target: float):
    if target <= current_wealth:
        return 0
    if monthly_capacity <= 0 and current_wealth <= 0:
        return None

    value = current_wealth
    monthly_return = (1 + annual_return) ** (1 / 12) - 1
    for month in range(1, 481):
        value = value * (1 + monthly_return) + max(monthly_capacity, 0)
        if value >= target:
            return month
    return None


def format_month_label(target_date: date):
    return f"{MONTH_LABELS[target_date.month - 1]} {target_date.year}"


def build_wealth_timeline(data_profile: dict, future_view: dict | None = None):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    annual_return = float((future_view or {}).get("annual_return") or 4.5) / 100
    today = date.today()
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
            months_to_target = 0
            estimated_date = today.isoformat()
            estimated_label = "Aujourd'hui"
        else:
            status = "achieved" if current_wealth >= target else "locked"
            progress = min(100, round((current_wealth / target) * 100, 1)) if target else 100
            months_to_target = estimate_months_to_target(
                current_wealth,
                monthly_capacity,
                annual_return,
                float(target),
            )
            if months_to_target is None:
                estimated_date = None
                estimated_label = "Date a confirmer"
            elif months_to_target == 0:
                estimated_date = today.isoformat()
                estimated_label = "Franchi"
            else:
                target_date = add_months(today, months_to_target)
                estimated_date = target_date.isoformat()
                estimated_label = format_month_label(target_date)
            if status == "locked" and next_stage is None:
                next_stage = {
                    "label": label,
                    "target": target,
                    "months_to_target": months_to_target,
                    "estimated_date": estimated_date,
                    "estimated_label": estimated_label,
                }

        timeline.append({
            "label": label,
            "target": target,
            "status": status,
            "progress_percent": progress,
            "distance_remaining": max(round(target - current_wealth, 2), 0) if target else 0,
            "months_to_target": months_to_target,
            "estimated_date": estimated_date,
            "estimated_label": estimated_label,
        })

    return {
        "current_wealth": round(current_wealth, 2),
        "monthly_velocity": round(monthly_capacity, 2),
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


def build_wealth_map(data_profile: dict, wealth_timeline: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_velocity = float(wealth_timeline.get("monthly_velocity") or 0)
    destination = wealth_timeline.get("next_milestone") or {"label": "1M", "target": 1000000}
    target = float(destination.get("target") or 1000000)

    return {
        "title": "Wealth Map",
        "destination": destination,
        "current_position": round(current_wealth, 2),
        "progress_percent": min(100, round((current_wealth / target) * 100, 1)) if target > 0 else 0,
        "distance_remaining": max(round(target - current_wealth, 2), 0),
        "monthly_velocity": round(monthly_velocity, 2),
        "estimated_label": destination.get("estimated_label"),
        "months_to_destination": destination.get("months_to_target"),
    }


def build_invisible_wealth(data_profile: dict, digital_twin: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    scenarios = digital_twin.get("scenarios") or []
    best = max(scenarios, key=lambda item: float(item.get("value_10y") or 0), default=None)
    projected = float((best or {}).get("value_10y") or current_wealth)

    return {
        "title": "Richesse invisible",
        "current_wealth": round(current_wealth, 2),
        "projected_wealth": round(projected, 2),
        "untapped_capital": max(round(projected - current_wealth, 2), 0),
        "best_path": best,
        "story": "Ecart entre la position actuelle et le meilleur futur simule par le backend.",
    }


def build_family_office_radar(data_profile: dict, weak_signals: dict, dependency_detector: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    portfolio_value = float(data_profile.get("portfolio_value") or 0)
    real_estate_value = float(data_profile.get("real_estate_value") or 0)
    business_value = float(data_profile.get("business_value") or 0)
    debt_total = float(data_profile.get("debt_total") or 0)
    concentration_flag = any(
        item.get("type") in {"concentration", "asset_concentration"}
        for item in (weak_signals.get("signals") or []) + (dependency_detector.get("signals") or [])
    )

    def status(score: int):
        if score >= 75:
            return "green"
        if score >= 45:
            return "amber"
        return "red"

    growth_score = 80 if monthly_capacity > 0 or business_value > 0 else 40
    diversification_domains = sum(1 for value in [portfolio_value, real_estate_value, business_value] if value > 0)
    diversification_score = 35 + diversification_domains * 20
    concentration_score = 35 if concentration_flag else 80
    income_score = 80 if data_profile.get("monthly_income", 0) else 35
    liquidity_score = 75 if monthly_capacity > 0 else 40
    debt_score = 40 if debt_total > max(current_wealth * 0.35, 1) else 75

    items = [
        ("growth", "Croissance", growth_score),
        ("diversification", "Diversification", diversification_score),
        ("concentration", "Concentration", concentration_score),
        ("income", "Revenus", income_score),
        ("liquidity", "Liquidite", liquidity_score),
        ("debt", "Dette", debt_score),
    ]

    return {
        "title": "Family Office Radar",
        "items": [
            {"key": key, "label": label, "score": min(100, score), "status": status(min(100, score))}
            for key, label, score in items
        ],
    }


def build_hidden_wealth(data_profile: dict, life_profile: dict | None = None):
    life_profile = life_profile or {}
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_income = float(data_profile.get("monthly_income") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    business_value = float(data_profile.get("business_value") or 0)
    professional = str(life_profile.get("professional_context") or "").lower()
    expertise_match = any(word in professional for word in ["marketing", "communication", "commerce", "business"])

    items = []
    if expertise_match or monthly_income > 0:
        expertise_value = max(monthly_income * 36, 75000 if expertise_match else 0)
        items.append({
            "key": "expertise",
            "label": "Expertise professionnelle",
            "potential_value": round(expertise_value, 2),
            "confidence": "contextual",
            "description": "Valeur potentielle de monetisation d'une competence deja presente.",
        })

    if expertise_match:
        items.append({
            "key": "network",
            "label": "Reseau professionnel",
            "potential_value": round(max(monthly_income * 12, 50000), 2),
            "confidence": "light",
            "description": "Potentiel commercial lie aux contacts et marches accessibles.",
        })

    if business_value > 0:
        items.append({
            "key": "business",
            "label": "Business existant",
            "potential_value": round(max(business_value * 2, business_value), 2),
            "confidence": "asset_based",
            "description": "Potentiel de valorisation ou de systematisation du bloc business.",
        })

    if monthly_capacity > 0:
        items.append({
            "key": "borrowing_capacity",
            "label": "Capacite d'emprunt theorique",
            "potential_value": round(monthly_capacity * 240, 2),
            "confidence": "simulation",
            "description": "Simulation prudente basee sur la capacite mensuelle, sans validation bancaire.",
        })

    activable = sum(float(item.get("potential_value") or 0) for item in items)
    return {
        "title": "Patrimoine cache",
        "visible_wealth": round(current_wealth, 2),
        "activable_wealth": round(activable, 2),
        "total_potential": round(current_wealth + activable, 2),
        "items": items,
        "basis": "Estimation backend de valeur activable, non comptabilisee comme patrimoine acquis.",
    }


def build_gravity_center(data_profile: dict, hidden_wealth: dict):
    visible_domains = [
        ("investments", "Financier", float(data_profile.get("portfolio_value") or 0)),
        ("real_estate", "Immobilier", float(data_profile.get("real_estate_value") or 0)),
        ("business", "Business", float(data_profile.get("business_value") or 0)),
    ]
    visible_total = sum(value for _, _, value in visible_domains)
    hidden_items = hidden_wealth.get("items") or []
    future_domains = visible_domains + [
        ("hidden", "Patrimoine activable", float(hidden_wealth.get("activable_wealth") or 0))
    ]
    future_total = sum(value for _, _, value in future_domains)
    dominant_visible = max(visible_domains, key=lambda item: item[2], default=("none", "Aucun", 0))
    dominant_future = max(future_domains, key=lambda item: item[2], default=("none", "Aucun", 0))

    return {
        "title": "Centre de gravite",
        "visible": [
            {
                "key": key,
                "label": label,
                "value": round(value, 2),
                "weight": round((value / visible_total) * 100, 1) if visible_total > 0 else 0,
            }
            for key, label, value in visible_domains
        ],
        "future": [
            {
                "key": key,
                "label": label,
                "value": round(value, 2),
                "weight": round((value / future_total) * 100, 1) if future_total > 0 else 0,
            }
            for key, label, value in future_domains
        ],
        "dominant_visible": dominant_visible[1],
        "dominant_future": dominant_future[1],
        "reading": (
            f"Le patrimoine visible depend surtout de {dominant_visible[1].lower()}, "
            f"mais le potentiel futur peut basculer vers {dominant_future[1].lower()}."
            if future_total > 0 else
            "Le centre de gravite sera lisible quand davantage de donnees seront renseignees."
        ),
        "hidden_count": len(hidden_items),
    }


def build_stress_tests(data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    real_estate_value = float(data_profile.get("real_estate_value") or 0)
    business_value = float(data_profile.get("business_value") or 0)
    portfolio_value = float(data_profile.get("portfolio_value") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)

    tests = [
        {
            "key": "real_estate_down_20",
            "label": "Immobilier -20%",
            "result_value": round(current_wealth - real_estate_value * 0.2, 2),
            "delta": round(-real_estate_value * 0.2, 2),
            "reading": "Mesure la sensibilite a une baisse immobiliere.",
        },
        {
            "key": "markets_down_15",
            "label": "Marches financiers -15%",
            "result_value": round(current_wealth - portfolio_value * 0.15, 2),
            "delta": round(-portfolio_value * 0.15, 2),
            "reading": "Mesure la sensibilite aux actifs financiers liquides.",
        },
        {
            "key": "business_double",
            "label": "Business x2",
            "result_value": round(current_wealth + business_value, 2),
            "delta": round(business_value, 2),
            "reading": "Mesure l'effet d'une acceleration business.",
        },
        {
            "key": "extra_500_month",
            "label": "+500 EUR/mois sur 10 ans",
            "result_value": round(current_wealth + (monthly_capacity + 500) * 12 * 10, 2),
            "delta": round(500 * 12 * 10, 2),
            "reading": "Mesure la puissance d'un effort mensuel additionnel avant rendement.",
        },
    ]

    return {
        "title": "Stress tests Family Office",
        "base_value": round(current_wealth, 2),
        "tests": tests,
    }


def build_leverage_engine(data_profile: dict, hidden_wealth: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    hidden_items = hidden_wealth.get("items") or []
    hidden_value = float(hidden_wealth.get("activable_wealth") or 0)

    levers = [
        {
            "key": "business",
            "label": "Developper le business",
            "impact_score": min(100, 45 + int(hidden_value / max(current_wealth or 1, 1) * 35)),
            "reason": "Fort si une expertise ou une valeur activable existe.",
        },
        {
            "key": "real_estate",
            "label": "Immobilier",
            "impact_score": 70 if monthly_capacity > 0 else 45,
            "reason": "Pertinent si la capacite mensuelle permet de soutenir le levier.",
        },
        {
            "key": "markets",
            "label": "Marches financiers",
            "impact_score": 60 if monthly_capacity > 0 else 40,
            "reason": "Robuste si l'investissement reste automatique et diversifie.",
        },
        {
            "key": "crypto",
            "label": "Crypto / actifs risqués",
            "impact_score": 35,
            "reason": "Levier secondaire tant que la base patrimoniale n'est pas stabilisee.",
        },
    ]
    levers = sorted(levers, key=lambda item: item["impact_score"], reverse=True)

    return {
        "title": "Moteur de leviers",
        "main_lever": levers[0] if levers else None,
        "levers": levers,
        "hidden_assets_count": len(hidden_items),
    }


def build_life_wealth(data_profile: dict, life_profile: dict | None = None):
    life_profile = life_profile or {}
    monthly_income = float(data_profile.get("monthly_income") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    current_wealth = float(data_profile.get("current_wealth") or 0)
    domains = sum(1 for value in [
        data_profile.get("portfolio_value", 0),
        data_profile.get("real_estate_value", 0),
        data_profile.get("business_value", 0),
    ] if float(value or 0) > 0)

    security = min(100, round((monthly_capacity * 6 / max(monthly_income or 1, 1)) * 100)) if monthly_income else 35
    freedom = min(100, round((current_wealth / 1000000) * 100, 1))
    transmission = 65 if life_profile.get("has_children") and current_wealth > 0 else 20
    diversification = min(100, 25 + domains * 20)
    growth = 70 if monthly_capacity > 0 or data_profile.get("business_value", 0) else 40

    return {
        "title": "Patrimoine de vie",
        "dimensions": [
            {"key": "security", "label": "Securite", "score": security},
            {"key": "freedom", "label": "Liberte", "score": freedom},
            {"key": "transmission", "label": "Transmission", "score": transmission},
            {"key": "diversification", "label": "Diversification", "score": diversification},
            {"key": "growth", "label": "Croissance", "score": growth},
        ],
    }


def build_future_film(data_profile: dict, digital_twin: dict, leverage_engine: dict):
    current_year = date.today().year
    current_wealth = float(data_profile.get("current_wealth") or 0)
    best = (digital_twin.get("scenarios") or [{}])[0]
    best_path = leverage_engine.get("main_lever") or {}
    value_5y = float(best.get("value_5y") or current_wealth)
    value_10y = float(best.get("value_10y") or value_5y)

    return {
        "title": "Film du futur patrimonial",
        "chapters": [
            {
                "year": current_year,
                "title": "La base devient visible",
                "wealth": round(current_wealth, 2),
                "narrative": "White Rock transforme la photo actuelle en point de depart mesurable.",
            },
            {
                "year": current_year + 2,
                "title": "Le levier prioritaire s'active",
                "wealth": round((current_wealth + value_5y) / 2, 2),
                "narrative": f"Le levier {str(best_path.get('label') or 'principal').lower()} commence a peser dans la trajectoire.",
            },
            {
                "year": current_year + 5,
                "title": "La trajectoire change d'echelle",
                "wealth": round(value_5y, 2),
                "narrative": "Les efforts recurrents et les actifs suivis commencent a creer une trajectoire composee.",
            },
            {
                "year": current_year + 10,
                "title": "Le futur alternatif devient tangible",
                "wealth": round(value_10y, 2),
                "narrative": "Le patrimoine projete n'est plus seulement une valeur: c'est une architecture de vie.",
            },
        ],
    }


def build_family_office_scorecard(data_profile: dict, life_profile: dict | None, life_wealth: dict):
    dimensions = {item.get("key"): item.get("score") for item in life_wealth.get("dimensions") or []}
    capital_score = min(100, round((float(data_profile.get("current_wealth") or 0) / 1000000) * 100, 1))
    revenue_score = min(100, round((float(data_profile.get("monthly_income") or 0) / 10000) * 100, 1))

    return {
        "title": "Family Office Scorecard",
        "dimensions": [
            {"key": "capital", "label": "Capital", "score": capital_score},
            {"key": "income", "label": "Revenus", "score": revenue_score},
            {"key": "resilience", "label": "Resilience", "score": dimensions.get("security", 0)},
            {"key": "diversification", "label": "Diversification", "score": dimensions.get("diversification", 0)},
            {"key": "growth", "label": "Croissance", "score": dimensions.get("growth", 0)},
            {"key": "transmission", "label": "Transmission", "score": dimensions.get("transmission", 0)},
        ],
    }


def build_board_briefing(personal_command_center: dict, gravity_center: dict, stress_tests: dict):
    tests = stress_tests.get("tests") or []
    downside = min(tests, key=lambda item: float(item.get("delta") or 0), default=None)

    return {
        "title": "Conseil d'administration personnel",
        "headline": personal_command_center.get("situation"),
        "what_changed": gravity_center.get("reading"),
        "main_risk": (personal_command_center.get("threat") or {}).get("title"),
        "main_opportunity": (personal_command_center.get("opportunity") or {}).get("title"),
        "stress_watch": downside,
        "next_step": personal_command_center.get("next_step"),
    }


def build_memorable_wealth_insight(
    data_profile: dict,
    hidden_wealth: dict,
    gravity_center: dict,
    wealth_map: dict,
    leverage_engine: dict,
):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    activable = float(hidden_wealth.get("activable_wealth") or 0)
    total_potential = float(hidden_wealth.get("total_potential") or 0)
    dominant_future = gravity_center.get("dominant_future")
    main_lever = leverage_engine.get("main_lever") or {}
    destination = wealth_map.get("destination") or {}
    estimated_label = wealth_map.get("estimated_label") or destination.get("estimated_label")

    if current_wealth > 0 and activable >= current_wealth * 2:
        ratio = round(activable / current_wealth, 1)
        return (
            f"Ton patrimoine activable represente environ {ratio} fois ton patrimoine visible: "
            "c'est probablement le signal le plus important a surveiller."
        )

    if dominant_future and main_lever.get("label"):
        return (
            f"Ton futur patrimonial semble moins dependre de ce que tu possedes deja "
            f"que de ta capacite a activer {str(main_lever.get('label')).lower()}."
        )

    if estimated_label:
        return f"A ce rythme, ton prochain palier patrimonial devient lisible autour de {estimated_label}."

    if total_potential > current_wealth:
        return "White Rock detecte deja plus de potentiel activable que de capital visible."

    return "Le premier enjeu est de rendre la trajectoire assez claire pour que chaque action compte."


def build_family_office_ceo_dashboard(
    data_profile: dict,
    strategic_intelligence: dict,
    wealth_narrative: dict,
    family_office_intelligence: dict,
    missions: list[dict],
):
    monthly_income = float(data_profile.get("monthly_income") or 0)
    monthly_expenses = float(data_profile.get("monthly_expenses") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    current_wealth = float(data_profile.get("current_wealth") or 0)
    debt_total = float(data_profile.get("debt_total") or 0)
    active_projects = int(data_profile.get("completed_steps") or 0)
    burn_rate = monthly_expenses
    runway_months = None

    if burn_rate > 0 and monthly_capacity < 0:
        runway_months = max(0, round(current_wealth / burn_rate, 1))
    elif monthly_capacity >= 0:
        runway_months = "stable"

    cards = strategic_intelligence.get("cards") or []
    decision = next((card for card in cards if card.get("key") == "decision"), {})
    risk = next((card for card in cards if card.get("key") == "risk"), {})
    scorecard = family_office_intelligence.get("scorecard") or []
    weakest_dimension = min(scorecard, key=lambda item: float(item.get("score") or 0), default=None)

    if monthly_capacity > 0:
        operating_reading = "Ton systeme produit une capacite mensuelle positive."
    elif monthly_income > 0:
        operating_reading = "Ton systeme genere du revenu, mais la marge de manoeuvre reste fragile."
    else:
        operating_reading = "Le cockpit doit encore consolider les revenus pour lire la marge reelle."

    return {
        "title": "Family Office CEO",
        "question": "Comment piloter ma vie financiere comme une holding personnelle ?",
        "operating_reading": operating_reading,
        "wealth": round(current_wealth, 2),
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses": round(monthly_expenses, 2),
        "monthly_capacity": round(monthly_capacity, 2),
        "burn_rate": round(burn_rate, 2),
        "runway_months": runway_months,
        "debt_total": round(debt_total, 2),
        "active_projects": active_projects,
        "objective": wealth_narrative.get("memorable_insight"),
        "decision": decision,
        "risk": risk,
        "weakest_dimension": weakest_dimension,
        "mission": missions[0] if missions else None,
    }


def build_wealth_intelligence(
    wealth_narrative: dict,
    family_office_view: dict,
    hidden_wealth: dict,
    gravity_center: dict,
):
    return {
        "title": "Wealth Intelligence",
        "question": "Ou j'en suis ?",
        "headline": wealth_narrative.get("headline"),
        "narrative": wealth_narrative.get("narrative"),
        "memorable_insight": wealth_narrative.get("memorable_insight"),
        "why_it_matters": wealth_narrative.get("why_it_matters"),
        "visible_wealth": wealth_narrative.get("visible_wealth"),
        "activable_wealth": wealth_narrative.get("activable_wealth"),
        "total_potential": wealth_narrative.get("total_potential"),
        "gravity_reading": gravity_center.get("reading") or wealth_narrative.get("gravity_reading"),
        "domains": family_office_view.get("allocation") or [],
        "hidden_items": hidden_wealth.get("items") or [],
    }


def build_decision_intelligence(strategic_intelligence: dict, family_office_ceo: dict):
    cards = strategic_intelligence.get("cards") or []
    decision = next((card for card in cards if card.get("key") == "decision"), {})
    risk = next((card for card in cards if card.get("key") == "risk"), {})
    opportunity = next((card for card in cards if card.get("key") == "opportunity"), {})
    leverage = next((card for card in cards if card.get("key") == "leverage"), {})

    return {
        "title": "Decision Intelligence",
        "question": "Qu'est-ce que je fais maintenant ?",
        "why_it_matters": "Une bonne interface patrimoniale ne montre pas toutes les possibilites: elle isole la decision utile.",
        "decision": decision,
        "risk": risk,
        "opportunity": opportunity,
        "leverage": leverage,
        "next_action": decision.get("action") or opportunity.get("action") or family_office_ceo.get("mission", {}).get("description"),
        "cards": [risk, opportunity, decision, leverage],
    }


def build_wealth_narrative(
    data_profile: dict,
    hidden_wealth: dict,
    gravity_center: dict,
    wealth_map: dict,
    leverage_engine: dict,
):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    activable = float(hidden_wealth.get("activable_wealth") or 0)
    destination = wealth_map.get("destination") or {}
    main_lever = leverage_engine.get("main_lever") or {}
    estimated_label = wealth_map.get("estimated_label") or destination.get("estimated_label")
    memorable_insight = build_memorable_wealth_insight(
        data_profile,
        hidden_wealth,
        gravity_center,
        wealth_map,
        leverage_engine,
    )

    if activable > current_wealth and main_lever.get("label"):
        narrative = (
            f"Ton patrimoine visible repose aujourd'hui sur une base mesurable. "
            f"Mais la lecture Family Office montre autre chose: ton potentiel futur peut se deplacer vers "
            f"{str(gravity_center.get('dominant_future') or 'un levier futur').lower()}, "
            f"avec {str(main_lever.get('label')).lower()} comme accelerateur principal. "
            "Ce n'est pas seulement une question de valeur detenue: c'est une question de capital encore activable."
        )
    elif estimated_label:
        narrative = (
            f"Ta trajectoire est maintenant lisible: le prochain palier patrimonial est estime autour de {estimated_label}. "
            "La valeur de White Rock ici n'est pas seulement de montrer le patrimoine, mais de rendre la distance, le rythme et la decision suivante visibles."
        )
    else:
        narrative = (
            "White Rock commence a transformer les donnees patrimoniales en trajectoire. "
            "Plus les revenus, actifs et objectifs seront renseignes, plus le recit deviendra precis."
        )

    return {
        "title": "Wealth Narrative",
        "headline": "Ce que raconte ta trajectoire",
        "narrative": narrative,
        "memorable_insight": memorable_insight,
        "why_it_matters": "Parce que les decisions patrimoniales deviennent plus simples quand la trajectoire raconte une histoire claire.",
        "visible_wealth": round(current_wealth, 2),
        "activable_wealth": round(activable, 2),
        "total_potential": hidden_wealth.get("total_potential"),
        "next_milestone": destination,
        "main_lever": main_lever,
        "gravity_reading": gravity_center.get("reading"),
    }


def build_future_intelligence(
    wealth_map: dict,
    wealth_timeline: dict,
    digital_twin: dict,
    wealth_gps: dict,
    future_film: dict,
):
    position = wealth_map.get("destination") or {}
    months_to_target = wealth_map.get("months_to_destination") or position.get("months_to_target")
    if months_to_target:
        time_to_next = f"{int(months_to_target)} mois"
        why_it_matters = (
            f"Le prochain palier n'est plus abstrait: il peut etre suivi comme une distance temporelle de {time_to_next}."
        )
    else:
        time_to_next = None
        why_it_matters = "Cette vue transforme le patrimoine en trajectoire, puis la trajectoire en decisions."

    return {
        "title": "Future Intelligence",
        "question": "Ou vais-je ?",
        "why_it_matters": why_it_matters,
        "time_to_next": time_to_next,
        "position": {
            "current": wealth_map.get("current_position"),
            "destination": wealth_map.get("destination"),
            "progress_percent": wealth_map.get("progress_percent"),
            "distance_remaining": wealth_map.get("distance_remaining"),
            "monthly_velocity": wealth_map.get("monthly_velocity"),
            "estimated_label": wealth_map.get("estimated_label"),
        },
        "timeline": wealth_timeline.get("stages") or [],
        "routes": wealth_gps.get("routes") or [],
        "simulations": digital_twin.get("scenarios") or [],
        "film": future_film.get("chapters") or [],
    }


def build_strategic_intelligence(
    mission_control: dict,
    opportunity_radar: dict,
    decision_engine: dict,
    leverage_engine: dict,
    board_briefing: dict,
):
    return {
        "title": "Strategic Intelligence",
        "question": "Que dois-je faire ?",
        "cards": [
            {
                "key": "risk",
                "label": "Risque principal",
                "title": (mission_control.get("risk") or {}).get("title"),
                "description": (mission_control.get("risk") or {}).get("description"),
            },
            {
                "key": "opportunity",
                "label": "Opportunite principale",
                "title": ((opportunity_radar.get("items") or [{}])[0]).get("title"),
                "description": ((opportunity_radar.get("items") or [{}])[0]).get("impact"),
                "action": ((opportunity_radar.get("items") or [{}])[0]).get("next_action"),
            },
            {
                "key": "decision",
                "label": "Decision du moment",
                "title": (mission_control.get("decision") or {}).get("title"),
                "description": (mission_control.get("decision") or {}).get("description"),
                "action": board_briefing.get("next_step"),
            },
            {
                "key": "leverage",
                "label": "Levier principal",
                "title": (leverage_engine.get("main_lever") or {}).get("label"),
                "description": (leverage_engine.get("main_lever") or {}).get("reason"),
                "score": (leverage_engine.get("main_lever") or {}).get("impact_score"),
            },
        ],
        "decision_matrix": decision_engine.get("decisions") or [],
    }


def build_family_office_intelligence(
    family_office_scorecard: dict,
    stress_tests: dict,
    dependency_detector: dict,
    weak_signals: dict,
    life_wealth: dict,
    family_office_radar: dict,
):
    return {
        "title": "Family Office Intelligence",
        "question": "Quelle est la solidite globale ?",
        "scorecard": family_office_scorecard.get("dimensions") or [],
        "stress_tests": stress_tests.get("tests") or [],
        "dependencies": dependency_detector.get("signals") or [],
        "weak_signals": weak_signals.get("signals") or [],
        "life_dimensions": life_wealth.get("dimensions") or [],
        "radar": family_office_radar.get("items") or [],
    }


def apply_plan_experience_gates(
    plan: str,
    wealth_intelligence: dict,
    future_intelligence: dict,
    strategic_intelligence: dict,
    decision_intelligence: dict,
    family_office_intelligence: dict,
    family_office_ceo: dict,
):
    normalized = normalize_plan(plan)

    if not plan_allows(normalized, "GOLD"):
        future_intelligence = {
            **future_intelligence,
            "routes": [],
            "simulations": [],
            "film": (future_intelligence.get("film") or [])[:2],
        }
        strategic_intelligence = None
        decision_intelligence = None
        family_office_intelligence = None
        family_office_ceo = None
        return {
            "wealth_intelligence": wealth_intelligence,
            "future_intelligence": future_intelligence,
            "strategic_intelligence": strategic_intelligence,
            "decision_intelligence": decision_intelligence,
            "family_office_intelligence": family_office_intelligence,
            "family_office_ceo": family_office_ceo,
        }

    if not plan_allows(normalized, "ELITE"):
        wealth_intelligence = {
            **wealth_intelligence,
            "hidden_items": (wealth_intelligence.get("hidden_items") or [])[:2],
        }
        future_intelligence = {
            **future_intelligence,
            "simulations": (future_intelligence.get("simulations") or [])[:1],
            "routes": (future_intelligence.get("routes") or [])[:1],
        }
        family_office_intelligence = {
            **family_office_intelligence,
            "stress_tests": (family_office_intelligence.get("stress_tests") or [])[:2],
            "dependencies": (family_office_intelligence.get("dependencies") or [])[:2],
            "weak_signals": [],
            "life_dimensions": [],
            "radar": [],
        }
        family_office_ceo = None

    if not plan_allows(normalized, "LIBERTY"):
        strategic_intelligence = {
            **strategic_intelligence,
            "decision_matrix": [],
            "advanced_arbitrages": [],
            "family_office_board": None,
        }
        decision_intelligence = {
            **decision_intelligence,
            "decision_matrix": [],
            "advanced_arbitrages": [],
            "family_office_board": None,
        }

    if not plan_allows(normalized, "LEGACY"):
        family_office_intelligence = {
            **family_office_intelligence,
            "dynasty_layer": None,
        } if family_office_intelligence else None

    return {
        "wealth_intelligence": wealth_intelligence,
        "future_intelligence": future_intelligence,
        "strategic_intelligence": strategic_intelligence,
        "decision_intelligence": decision_intelligence,
        "family_office_intelligence": family_office_intelligence,
        "family_office_ceo": family_office_ceo,
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
        wealth_timeline = build_wealth_timeline(data_profile, future_view)
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
        wealth_map = build_wealth_map(data_profile, wealth_timeline)
        invisible_wealth = build_invisible_wealth(data_profile, digital_twin)
        family_office_radar = build_family_office_radar(data_profile, weak_signals, dependency_detector)
        hidden_wealth = build_hidden_wealth(data_profile, life_profile)
        gravity_center = build_gravity_center(data_profile, hidden_wealth)
        stress_tests = build_stress_tests(data_profile)
        leverage_engine = build_leverage_engine(data_profile, hidden_wealth)
        life_wealth = build_life_wealth(data_profile, life_profile)
        future_film = build_future_film(data_profile, digital_twin, leverage_engine)
        family_office_scorecard = build_family_office_scorecard(data_profile, life_profile, life_wealth)
        board_briefing = build_board_briefing(personal_command_center, gravity_center, stress_tests)
        wealth_narrative = build_wealth_narrative(
            data_profile,
            hidden_wealth,
            gravity_center,
            wealth_map,
            leverage_engine,
        )
        future_intelligence = build_future_intelligence(
            wealth_map,
            wealth_timeline,
            digital_twin,
            wealth_gps,
            future_film,
        )
        strategic_intelligence = build_strategic_intelligence(
            mission_control,
            opportunity_radar,
            decision_engine,
            leverage_engine,
            board_briefing,
        )
        family_office_intelligence = build_family_office_intelligence(
            family_office_scorecard,
            stress_tests,
            dependency_detector,
            weak_signals,
            life_wealth,
            family_office_radar,
        )
        family_office_ceo = build_family_office_ceo_dashboard(
            data_profile,
            strategic_intelligence,
            wealth_narrative,
            family_office_intelligence,
            missions,
        )
        wealth_intelligence = build_wealth_intelligence(
            wealth_narrative,
            family_office_view,
            hidden_wealth,
            gravity_center,
        )
        decision_intelligence = build_decision_intelligence(
            strategic_intelligence,
            family_office_ceo,
        )
        gated_experience = apply_plan_experience_gates(
            plan,
            wealth_intelligence,
            future_intelligence,
            strategic_intelligence,
            decision_intelligence,
            family_office_intelligence,
            family_office_ceo,
        )
        wealth_intelligence = gated_experience["wealth_intelligence"]
        future_intelligence = gated_experience["future_intelligence"]
        strategic_intelligence = gated_experience["strategic_intelligence"]
        decision_intelligence = gated_experience["decision_intelligence"]
        family_office_intelligence = gated_experience["family_office_intelligence"]
        family_office_ceo = gated_experience["family_office_ceo"]

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
        "wealth_map": wealth_map,
        "invisible_wealth": invisible_wealth,
        "family_office_radar": family_office_radar,
        "hidden_wealth": hidden_wealth,
        "gravity_center": gravity_center,
        "stress_tests": stress_tests,
        "leverage_engine": leverage_engine,
        "life_wealth": life_wealth,
        "future_film": future_film,
        "family_office_scorecard": family_office_scorecard,
        "board_briefing": board_briefing,
        "wealth_narrative": wealth_narrative,
        "wealth_intelligence": wealth_intelligence,
        "future_intelligence": future_intelligence,
        "strategic_intelligence": strategic_intelligence,
        "decision_intelligence": decision_intelligence,
        "family_office_intelligence": family_office_intelligence,
        "family_office_ceo": family_office_ceo,
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
