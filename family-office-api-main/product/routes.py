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
