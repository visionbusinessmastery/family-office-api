# =========================
# ADVISOR ROUTES V4 CLEAN
# =========================

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from auth.utils import get_current_user
from core.utils import safe_execute
from core.limiter import limiter
from database import engine
from security.abuse_engine import assert_ethan_limit
from security.audit import ensure_security_tables, log_security_event
from advisor.observability import (
    cost_by_day,
    cost_by_model,
    cost_by_plan,
    ensure_ethan_observability_tables,
    top_expensive_users,
)

from .schemas import AdvisorRequest
from .security_engine import inspect_advisor_prompt

from .service import (
    ensure_ethan_ai_tables,
    get_user_plan,
    get_advisor_free,
    portfolio_autopilot,
    portfolio_manager,
)
from analytics.analytics_events import ETHAN_USED
from analytics.posthog_service import capture_event

router = APIRouter()


@router.post("/")
@router.post("/advisor")
@limiter.limit("10/minute")
def advisor(request: Request, data: AdvisorRequest):

    def _run():
        user_email = request.state.user_email
        message = inspect_advisor_prompt(data.message)

        with engine.begin() as conn:
            ensure_security_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            assert_ethan_limit(conn, request, user_email, plan)
            log_security_event(
                conn,
                "ethan_request",
                request,
                email=user_email,
                user_id=user_id,
                metadata={"endpoint": "advisor", "chars": len(message)},
            )
            capture_event(conn, ETHAN_USED, user_id=user_id, email=user_email, properties={"endpoint": "advisor", "plan": plan})

        result = get_advisor_free(user_email, message)

        return {
            "user": user_email,
            "system": "ADVISOR_CHAT_V4",
            "input": message,
            "result": result
        }

    return safe_execute(_run, module_name="ADVISOR_CHAT")


# =========================
# 2. PORTFOLIO ANALYSIS (READ ONLY)
# =========================
@router.post("/advisor/portfolio")
@limiter.limit("10/minute")
def advisor_portfolio(request: Request, data: AdvisorRequest):

    def _run():
        user_email = request.state.user_email
        message = inspect_advisor_prompt(data.message)

        with engine.begin() as conn:
            ensure_security_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            assert_ethan_limit(conn, request, user_email, plan)
            log_security_event(
                conn,
                "ethan_request",
                request,
                email=user_email,
                user_id=user_id,
                metadata={"endpoint": "advisor_portfolio", "chars": len(message)},
            )
            capture_event(conn, ETHAN_USED, user_id=user_id, email=user_email, properties={"endpoint": "advisor_portfolio", "plan": plan})

        result = portfolio_manager(user_email, message)

        return {
            "user": user_email,
            "system": "PORTFOLIO_ANALYSIS_V4",
            "input": message,
            "result": result
        }

    return safe_execute(_run, module_name="PORTFOLIO_MANAGER")


# =========================
# 3. AUTOPILOT ENGINE (SIMULATION / DECISION)
# =========================
@router.post("/advisor/autopilot")
@limiter.limit("10/minute")
def advisor_autopilot(request: Request, data: AdvisorRequest):

    def _run():
        user_email = request.state.user_email
        message = inspect_advisor_prompt(data.message)

        with engine.begin() as conn:
            ensure_security_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            assert_ethan_limit(conn, request, user_email, plan)
            log_security_event(
                conn,
                "ethan_request",
                request,
                email=user_email,
                user_id=user_id,
                metadata={"endpoint": "advisor_autopilot", "chars": len(message)},
            )
            capture_event(conn, ETHAN_USED, user_id=user_id, email=user_email, properties={"endpoint": "advisor_autopilot", "plan": plan})

        result = portfolio_autopilot(user_email, message)

        return {
            "user": user_email,
            "system": "AUTOPILOT_ENGINE_V4",
            "mode": "SIMULATION",
            "input": message,
            "result": result
        }

    return safe_execute(_run, module_name="AUTOPILOT_ENGINE")


@router.get("/usage")
def advisor_usage(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_ethan_ai_tables(conn)
        user = conn.execute(text("""
            SELECT id
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        rows = conn.execute(text("""
            SELECT
                plan,
                tier,
                model,
                COUNT(*) AS requests,
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
                COALESCE(SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END), 0) AS cache_hits
            FROM ethan_usage_events
            WHERE user_id = :user_id
              AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY plan, tier, model
            ORDER BY estimated_cost_usd DESC
        """), {"user_id": user.id}).fetchall()

    return {
        "window_days": 30,
        "usage": [
            {
                "plan": row.plan,
                "tier": row.tier,
                "model": row.model,
                "requests": int(row.requests or 0),
                "input_tokens": int(row.input_tokens or 0),
                "output_tokens": int(row.output_tokens or 0),
                "estimated_cost_usd": float(row.estimated_cost_usd or 0),
                "cache_hit_ratio": (
                    round(float(row.cache_hits or 0) / float(row.requests or 1), 3)
                ),
            }
            for row in rows
        ],
    }


@router.get("/admin/usage")
def advisor_admin_usage(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_ethan_ai_tables(conn)
        requester = conn.execute(text("""
            SELECT plan
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        if not requester or str(requester.plan or "").upper() not in ["LEGACY", "LIBERTY"]:
            raise HTTPException(status_code=403, detail="Admin usage unavailable")

        rows = conn.execute(text("""
            SELECT
                plan,
                model,
                COUNT(*) AS requests,
                COUNT(DISTINCT user_id) AS users,
                COALESCE(SUM(input_tokens), 0) AS input_tokens,
                COALESCE(SUM(output_tokens), 0) AS output_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
                COALESCE(SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END), 0) AS cache_hits
            FROM ethan_usage_events
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY plan, model
            ORDER BY estimated_cost_usd DESC
        """)).fetchall()

    return {
        "window_days": 30,
        "plans": [
            {
                "plan": row.plan,
                "model": row.model,
                "requests": int(row.requests or 0),
                "users": int(row.users or 0),
                "input_tokens": int(row.input_tokens or 0),
                "output_tokens": int(row.output_tokens or 0),
                "estimated_cost_usd": float(row.estimated_cost_usd or 0),
                "cache_hit_ratio": round(float(row.cache_hits or 0) / float(row.requests or 1), 3),
            }
            for row in rows
        ],
    }


@router.get("/admin/costs")
def advisor_admin_costs(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_ethan_ai_tables(conn)
        ensure_ethan_observability_tables(conn)
        requester = conn.execute(text("""
            SELECT plan
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        if not requester or str(requester.plan or "").upper() not in ["LEGACY", "LIBERTY"]:
            raise HTTPException(status_code=403, detail="Admin costs unavailable")

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
                    "users": int(row.users or 0),
                    "estimated_cost_usd": float(row.estimated_cost_usd or 0),
                    "cache_hit_ratio": round(float(row.cache_hits or 0) / float(row.requests or 1), 3),
                }
                for row in cost_by_plan(conn)
            ],
        }


@router.get("/admin/models")
def advisor_admin_models(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        requester = conn.execute(text("SELECT plan FROM users WHERE email = :email"), {"email": email}).fetchone()
        if not requester or str(requester.plan or "").upper() not in ["LEGACY", "LIBERTY"]:
            raise HTTPException(status_code=403, detail="Admin models unavailable")
        return {
            "models": [
                {
                    "model": row.model,
                    "requests": int(row.requests or 0),
                    "estimated_cost_usd": float(row.estimated_cost_usd or 0),
                    "input_tokens": int(row.input_tokens or 0),
                    "output_tokens": int(row.output_tokens or 0),
                }
                for row in cost_by_model(conn)
            ]
        }


@router.get("/admin/usage-breakdown")
def advisor_admin_usage_breakdown(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        requester = conn.execute(text("SELECT plan FROM users WHERE email = :email"), {"email": email}).fetchone()
        if not requester or str(requester.plan or "").upper() not in ["LEGACY", "LIBERTY"]:
            raise HTTPException(status_code=403, detail="Admin usage unavailable")
        return {
            "top_users": [
                {
                    "email": row.email,
                    "plan": row.plan,
                    "requests": int(row.requests or 0),
                    "estimated_cost_usd": float(row.estimated_cost_usd or 0),
                }
                for row in top_expensive_users(conn)
            ]
        }
