from fastapi import APIRouter, Depends, Request

from advisor.observability import cost_by_day, cost_by_model, cost_by_plan, ensure_ethan_observability_tables
from analytics.posthog_service import ensure_analytics_tables
from auth.utils import get_current_user
from database import engine
from feature_flags.engine import ensure_feature_flags_table, list_feature_flags
from monitoring.health import system_health
from security.audit import require_security_admin


router = APIRouter()


HYBRID_SOURCE_MAP = {
    "score": {
        "primary_view": "/intelligence/global-command-center",
        "parallel_sources": [
            "/intelligence/user-intelligence",
            "/intelligence/score/recalculate",
        ],
        "frontend_fallbacks": "preserved",
        "notes": "Global Command Center is the dashboard view, but legacy score sources remain active.",
    },
    "opportunities": {
        "primary_view": "/intelligence/global-command-center",
        "parallel_sources": [
            "/intelligence/category-opportunities",
            "/intelligence/opportunity-intelligence",
        ],
        "frontend_fallbacks": "preserved",
        "notes": "Category and deal-flow opportunity systems intentionally coexist.",
    },
    "gamification": {
        "primary_view": "/gamification/",
        "parallel_sources": [
            "/product/context",
            "/intelligence/global-command-center",
        ],
        "frontend_fallbacks": "preserved",
        "notes": "Dedicated gamification API is the progression view; product context and command center keep auxiliary state.",
    },
    "portfolio_finance": {
        "primary_view": "domain services",
        "parallel_sources": [
            "/portfolio/",
            "/portfolio/history",
            "/finance/",
            "/real-estate/",
            "/yield-assets/",
            "/venture-assets/",
        ],
        "frontend_fallbacks": "preserved",
        "notes": "Backend domain totals and frontend consolidated portfolio calculations intentionally coexist.",
    },
}


def safe_mode_payload():
    return {
        "mode": "safe_stabilization",
        "live_comparison": "not_executed_safe_mode",
        "behavior": "read_only_observability",
        "source_map": HYBRID_SOURCE_MAP,
        "guarantees": [
            "no business logic execution",
            "no source unification",
            "no fallback removal",
            "no API contract changes to existing endpoints",
        ],
    }


@router.get("/admin/diagnostics")
def admin_diagnostics(request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        require_security_admin(conn, email, request)
        ensure_feature_flags_table(conn)
        ensure_analytics_tables(conn)
        ensure_ethan_observability_tables(conn)
        flags = list_feature_flags(conn)
        costs = cost_by_plan(conn, 7)
        models = cost_by_model(conn, 7)

    return {
        "health": system_health(),
        "feature_flags": [
            {
                "key": row.key,
                "enabled": bool(row.enabled),
                "rollout_percentage": int(row.rollout_percentage or 0),
                "subscription_min": row.subscription_min,
            }
            for row in flags
        ],
        "ethan_costs_7d": [
            {
                "plan": row.plan,
                "requests": int(row.requests or 0),
                "users": int(row.users or 0),
                "estimated_cost_usd": float(row.estimated_cost_usd or 0),
                "cache_hit_ratio": round(float(row.cache_hits or 0) / float(row.requests or 1), 3),
            }
            for row in costs
        ],
        "ethan_models_7d": [
            {
                "model": row.model,
                "requests": int(row.requests or 0),
                "estimated_cost_usd": float(row.estimated_cost_usd or 0),
            }
            for row in models
        ],
    }


@router.get("/admin/system-state")
def admin_system_state(request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        require_security_admin(conn, email, request)

    return {
        "health": system_health(),
        **safe_mode_payload(),
    }


@router.get("/admin/mismatch-report")
def admin_mismatch_report(request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        require_security_admin(conn, email, request)

    return {
        **safe_mode_payload(),
        "findings": [],
        "status": "no_live_mismatch_check_performed",
        "instructions": "Use this endpoint as a passive source map. Manual review is required before any correction.",
    }


@router.get("/admin/ethan-costs")
def admin_ethan_costs(request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        require_security_admin(conn, email, request)
        return {
            "by_day": [
                {
                    "day": str(row.day),
                    "plan": row.plan,
                    "model": row.model,
                    "requests": int(row.requests or 0),
                    "estimated_cost_usd": float(row.estimated_cost_usd or 0),
                    "cache_hit_ratio": round(float(row.cache_hits or 0) / float(row.requests or 1), 3),
                }
                for row in cost_by_day(conn)
            ],
            "by_plan": [
                {
                    "plan": row.plan,
                    "requests": int(row.requests or 0),
                    "estimated_cost_usd": float(row.estimated_cost_usd or 0),
                }
                for row in cost_by_plan(conn)
            ],
        }
