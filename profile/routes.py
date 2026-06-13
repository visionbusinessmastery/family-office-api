from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from core.cache import delete_cache_patterns
from database import engine
from intelligence.user_intelligence_engine import compute_user_intelligence
from portfolio.real_estate_routes import build_response as build_real_estate_response
from portfolio.real_estate_routes import get_real_estate_rows
from portfolio.service import get_user_portfolio
from portfolio.specialized_assets_routes import (
    build_business_intelligence,
    ensure_venture_table,
    ensure_yield_table,
)
from product.entitlements import resolve_effective_plan
from intelligence.weekly_report_service import build_daily_loop_report
from product.routes import (
    attach_daily_briefing_loop,
    build_data_profile,
    build_future_view,
    build_mission_control,
    build_missions,
    build_strategic_brief,
    build_wealth_academy,
    get_academy_progress,
    get_daily_briefing_loop,
    get_mission_progress,
)
from product.daily_briefing import build_ceo_daily_briefing
from profile.report_config import get_report_config


router = APIRouter()
_profile_schema_ready = False


def ensure_profile_tables(conn):
    global _profile_schema_ready

    if _profile_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_wealth_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            first_name TEXT,
            bio TEXT,
            avatar_url TEXT,
            goals TEXT,
            horizon TEXT,
            investor_profile TEXT,
            risk_level TEXT,
            main_currency TEXT DEFAULT 'EUR',
            motivation TEXT,
            has_children BOOLEAN DEFAULT FALSE,
            transmission_goal TEXT,
            expatriation_interest TEXT,
            governance_need TEXT,
            confidentiality_need TEXT,
            family_strategy TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS bio TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS has_children BOOLEAN DEFAULT FALSE"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS transmission_goal TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS expatriation_interest TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS governance_need TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS confidentiality_need TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS family_strategy TEXT"))

    _profile_schema_ready = True


def row_to_profile(row):
    if not row:
        return {
            "first_name": None,
            "bio": None,
            "avatar_url": None,
            "goals": [],
            "horizon": None,
            "investor_profile": None,
            "risk_level": None,
            "main_currency": "EUR",
            "motivation": None,
            "has_children": False,
            "transmission_goal": None,
            "expatriation_interest": None,
            "governance_need": None,
            "confidentiality_need": None,
            "family_strategy": None,
        }

    goals = [item for item in (row.goals or "").split("|") if item]

    return {
        "first_name": row.first_name,
        "bio": row.bio,
        "avatar_url": row.avatar_url,
        "goals": goals,
        "horizon": row.horizon,
        "investor_profile": row.investor_profile,
        "risk_level": row.risk_level,
        "main_currency": row.main_currency or "EUR",
        "motivation": row.motivation,
        "has_children": bool(row.has_children),
        "transmission_goal": row.transmission_goal,
        "expatriation_interest": row.expatriation_interest,
        "governance_need": row.governance_need,
        "confidentiality_need": row.confidentiality_need,
        "family_strategy": row.family_strategy,
    }


def _safe_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _mask(value, enabled: bool):
    if not enabled:
        return value
    if not value:
        return value
    return "Masque"


def _portfolio_allocation(portfolio: dict):
    items = portfolio.get("portfolio") or []
    totals = {}
    for item in items:
        label = item.get("asset_type") or item.get("category") or "Autre"
        totals[label] = totals.get(label, 0.0) + _safe_float(
            item.get("current_value") or item.get("value")
        )
    total = sum(totals.values())
    return [
        {
            "label": label,
            "value": round(value, 2),
            "percent": round((value / total * 100) if total > 0 else 0, 2),
        }
        for label, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def _finance_totals_from_data_profile(data_profile: dict):
    income = _safe_float(data_profile.get("monthly_income"))
    expenses = _safe_float(data_profile.get("monthly_expenses"))
    savings = _safe_float(data_profile.get("liquid_assets"))
    debt = _safe_float(data_profile.get("debt_total"))
    cashflow = income - expenses
    return {
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "cashflow": round(cashflow, 2),
        "savings": round(savings, 2),
        "debt": round(debt, 2),
        "security_reserve": round(_safe_float(data_profile.get("security_reserve")), 2),
        "mobilizable_liquidity": round(_safe_float(data_profile.get("mobilizable_liquidity")), 2),
        "deployable_liquidity": round(_safe_float(data_profile.get("deployable_liquidity")), 2),
        "liquid_months": round((savings / expenses) if expenses > 0 else 0, 2),
        "debt_to_income": round((debt / income) if income > 0 else 0, 2),
    }


def _wealth_breakdown(data_profile: dict):
    return [
        {"label": "Marches financiers", "value": _safe_float(data_profile.get("portfolio_value"))},
        {"label": "Immobilier", "value": _safe_float(data_profile.get("real_estate_value"))},
        {"label": "Business", "value": _safe_float(data_profile.get("business_value"))},
        {"label": "Liquidite mobilisable", "value": _safe_float(data_profile.get("deployable_liquidity"))},
    ]


@router.get("/me")
def get_profile(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_profile_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        row = conn.execute(text("""
            SELECT first_name, bio, avatar_url, goals, horizon, investor_profile,
                   risk_level, main_currency, motivation, has_children,
                   transmission_goal, expatriation_interest, governance_need,
                   confidentiality_need, family_strategy
            FROM user_wealth_profiles
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()

    return {"profile": row_to_profile(row)}


@router.put("/me")
def update_profile(data: dict, email: str = Depends(get_current_user)):
    goals = data.get("goals") or []

    if isinstance(goals, str):
        goals_text = goals
    else:
        goals_text = "|".join(str(goal) for goal in goals if goal)

    with engine.begin() as conn:
        ensure_profile_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        conn.execute(text("""
            INSERT INTO user_wealth_profiles (
                user_id, first_name, bio, avatar_url, goals, horizon,
                investor_profile, risk_level, main_currency, motivation,
                has_children, transmission_goal, expatriation_interest,
                governance_need, confidentiality_need, family_strategy, updated_at
            )
            VALUES (
                :user_id, :first_name, :bio, :avatar_url, :goals, :horizon,
                :investor_profile, :risk_level, :main_currency, :motivation,
                :has_children, :transmission_goal, :expatriation_interest,
                :governance_need, :confidentiality_need, :family_strategy, NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                first_name = EXCLUDED.first_name,
                bio = EXCLUDED.bio,
                avatar_url = EXCLUDED.avatar_url,
                goals = EXCLUDED.goals,
                horizon = EXCLUDED.horizon,
                investor_profile = EXCLUDED.investor_profile,
                risk_level = EXCLUDED.risk_level,
                main_currency = EXCLUDED.main_currency,
                motivation = EXCLUDED.motivation,
                has_children = EXCLUDED.has_children,
                transmission_goal = EXCLUDED.transmission_goal,
                expatriation_interest = EXCLUDED.expatriation_interest,
                governance_need = EXCLUDED.governance_need,
                confidentiality_need = EXCLUDED.confidentiality_need,
                family_strategy = EXCLUDED.family_strategy,
                updated_at = NOW()
        """), {
            "user_id": user_id,
            "first_name": data.get("first_name"),
            "bio": data.get("bio"),
            "avatar_url": data.get("avatar_url"),
            "goals": goals_text,
            "horizon": data.get("horizon"),
            "investor_profile": data.get("investor_profile"),
            "risk_level": data.get("risk_level"),
            "main_currency": data.get("main_currency") or "EUR",
            "motivation": data.get("motivation"),
            "has_children": bool(data.get("has_children")),
            "transmission_goal": data.get("transmission_goal"),
            "expatriation_interest": data.get("expatriation_interest"),
            "governance_need": data.get("governance_need"),
            "confidentiality_need": data.get("confidentiality_need"),
            "family_strategy": data.get("family_strategy"),
        })

    delete_cache_patterns(
        f"intel:{email}*",
        f"context:{email}*",
        f"product:{email}*",
        f"advisor:{email}*",
    )

    return {"status": "ok"}


@router.get("/wealth-report")
def get_wealth_report(
    mask_sensitive: bool = Query(False),
    email: str = Depends(get_current_user),
):
    with engine.begin() as conn:
        ensure_profile_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        user = conn.execute(text("""
            SELECT
                users.email,
                users.plan AS user_plan,
                users.profile_completed,
                users.revenus_mensuels,
                users.charges_mensuelles,
                subscriptions.plan AS subscription_plan,
                subscriptions.status AS subscription_status
            FROM users
            LEFT JOIN subscriptions ON subscriptions.user_id = users.id
            WHERE users.id = :user_id
        """), {"user_id": user_id}).fetchone()

        profile_row = conn.execute(text("""
            SELECT first_name, bio, avatar_url, goals, horizon, investor_profile,
                   risk_level, main_currency, motivation, has_children,
                   transmission_goal, expatriation_interest, governance_need,
                   confidentiality_need, family_strategy
            FROM user_wealth_profiles
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()

        data_profile = build_data_profile(conn, user_id)
        real_estate_payload = build_real_estate_response(get_real_estate_rows(conn, user_id))

        ensure_yield_table(conn)
        ensure_venture_table(conn)
        yield_rows = conn.execute(text("""
            SELECT *
            FROM yield_assets
            WHERE user_id = :user_id
            ORDER BY created_at DESC, id DESC
        """), {"user_id": user_id}).fetchall()
        venture_rows = conn.execute(text("""
            SELECT *
            FROM venture_assets
            WHERE user_id = :user_id
            ORDER BY created_at DESC, id DESC
        """), {"user_id": user_id}).fetchall()
        business_payload = build_business_intelligence(yield_rows, venture_rows)

    profile = row_to_profile(profile_row)
    effective_plan = resolve_effective_plan(
        user.user_plan,
        user.subscription_plan,
        user.subscription_status,
    )
    portfolio_payload = get_user_portfolio(user_id, use_cache=False)
    intelligence = compute_user_intelligence(email) or {}
    finance_totals = _finance_totals_from_data_profile(data_profile)
    visible_wealth = _safe_float(data_profile.get("current_wealth"))
    projected_wealth = _safe_float(data_profile.get("projection_wealth"))
    with engine.begin() as conn:
        score_value = int(intelligence.get("global_score") or 0)
        academy_progress = get_academy_progress(conn, user_id)
        mission_progress = get_mission_progress(conn, user_id)
        missions = build_missions(data_profile, score_value, effective_plan, academy_progress, mission_progress)
        wealth_academy = build_wealth_academy(data_profile, missions, score_value, effective_plan, academy_progress)
        strategic_brief = build_strategic_brief(data_profile, score_value, effective_plan)
        future_view = build_future_view(data_profile, score_value, effective_plan)
        mission_control = build_mission_control(strategic_brief, missions, future_view)
        daily_loop = get_daily_briefing_loop(conn, user_id)
        briefing = build_ceo_daily_briefing(
            data_profile,
            score_value,
            effective_plan,
            missions,
            mission_control,
            future_view,
            {},
            {},
            profile.get("first_name"),
            wealth_academy,
            daily_loop,
        )
        briefing = attach_daily_briefing_loop(
            briefing,
            daily_loop,
        )
        daily_loop_report = build_daily_loop_report(conn, user_id, "wealth_report")

    score = intelligence.get("family_office_score") or {}
    opportunities = intelligence.get("opportunities") or []
    if isinstance(opportunities, dict):
        opportunities = opportunities.get("opportunities") or opportunities.get("items") or []

    return {
        "version": "wealth-report-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mask_sensitive": mask_sensitive,
        "company": get_report_config(),
        "legal": {
            "disclaimer": get_report_config()["disclaimer"],
            "data_notice": get_report_config()["data_notice"],
            "source_of_truth": "Backend White Rock",
        },
        "user": {
            "email": _mask(user.email, mask_sensitive),
            "plan": effective_plan,
            "profile_completed": bool(user.profile_completed),
            "first_name": _mask(profile.get("first_name"), mask_sensitive),
        },
        "profile": {
            **profile,
            "first_name": _mask(profile.get("first_name"), mask_sensitive),
            "bio": _mask(profile.get("bio"), mask_sensitive),
        },
        "finance": {
            "totals": finance_totals,
            "chart": [
                {"label": "Revenus", "value": finance_totals["income"]},
                {"label": "Charges", "value": finance_totals["expenses"]},
                {"label": "Cashflow", "value": finance_totals["cashflow"]},
                {"label": "Liquidites", "value": finance_totals["savings"]},
                {"label": "Dettes", "value": finance_totals["debt"]},
            ],
        },
        "wealth": {
            "visible_wealth": round(visible_wealth, 2),
            "projected_wealth": round(projected_wealth, 2),
            "potential_gap": round(max(projected_wealth - visible_wealth, 0), 2),
            "completion_percent": data_profile.get("completion_percent"),
            "breakdown": _wealth_breakdown(data_profile),
        },
        "portfolio": {
            **portfolio_payload,
            "allocation": _portfolio_allocation(portfolio_payload),
        },
        "real_estate": real_estate_payload,
        "business": business_payload,
        "intelligence": {
            "global_score": intelligence.get("global_score"),
            "level": intelligence.get("level"),
            "score_details": score.get("details", {}),
            "advice": intelligence.get("advice") or score.get("advice") or [],
            "opportunities": opportunities[:8],
        },
        "ceo_daily_briefing": briefing,
        "daily_loop_report": daily_loop_report,
        "sources": [
            "users",
            "user_wealth_profiles",
            "finance_items",
            "portfolio",
            "real_estate_assets",
            "yield_assets",
            "venture_assets",
            "intelligence engine",
        ],
    }
