# =========================
# ADVISOR ROUTES V4 CLEAN
# =========================

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from auth.utils import get_current_user, get_email_from_request
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
from .autopilot_service import portfolio_autopilot

from .schemas import AdvisorRequest
from .security_engine import inspect_advisor_prompt

from .ethan.contract_validator import validate_ethan_frontend_contract
from .ethan.persistence_engine import (
    ensure_ethan_ai_tables,
    get_user_plan,
)
from .ethan_core import run_ethan_chat
from analytics.analytics_events import AUTOPILOT_SIMULATION_USED, ETHAN_USED
from analytics.posthog_service import capture_event
from advisor.ethan.memory_engine import (
    build_life_context,
    extract_context_signals,
    get_memory,
    summarize_context_profile,
)
from product.entitlements import plan_allows
from profile.routes import ensure_profile_tables

router = APIRouter()


ALLOWED_PROFILE_UPDATE_FIELDS = {
    "investor_profile",
    "has_children",
    "goals",
    "horizon",
    "risk_level",
    "motivation",
    "transmission_goal",
    "family_strategy",
}


def ensure_ethan_action_tables(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ethan_profile_update_proposals (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            field TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT NOT NULL,
            source TEXT DEFAULT 'conversation',
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            resolved_at TIMESTAMP
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ethan_document_inbox (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            filename TEXT,
            document_type TEXT,
            extracted_data JSONB DEFAULT '{}'::jsonb,
            proposed_updates JSONB DEFAULT '[]'::jsonb,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            resolved_at TIMESTAMP
        )
    """))


def require_plan(plan: str, minimum: str, feature: str):
    if not plan_allows(plan, minimum):
        raise HTTPException(
            status_code=403,
            detail={"error": "feature_locked", "feature": feature, "required_plan": minimum},
        )


def _profile_value(row, field):
    if not row:
        return None
    return getattr(row, field, None)


def _normalize_profile_value(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def _insert_profile_proposal(conn, user_id, field, old_value, new_value, source):
    if field not in ALLOWED_PROFILE_UPDATE_FIELDS:
        raise HTTPException(status_code=400, detail="Profile field not allowed")
    if _normalize_profile_value(old_value) == _normalize_profile_value(new_value):
        return None

    existing = conn.execute(text("""
        SELECT id, field, old_value, new_value, status, created_at
        FROM ethan_profile_update_proposals
        WHERE user_id = :user_id
          AND field = :field
          AND status = 'pending'
        ORDER BY created_at DESC
        LIMIT 1
    """), {"user_id": user_id, "field": field}).fetchone()

    if existing:
        return {
            "id": existing.id,
            "field": existing.field,
            "old_value": existing.old_value,
            "new_value": existing.new_value,
            "status": existing.status,
            "created_at": str(existing.created_at),
        }

    row = conn.execute(text("""
        INSERT INTO ethan_profile_update_proposals (
            user_id, field, old_value, new_value, source
        )
        VALUES (
            :user_id, :field, :old_value, :new_value, :source
        )
        RETURNING id, field, old_value, new_value, status, created_at
    """), {
        "user_id": user_id,
        "field": field,
        "old_value": None if old_value is None else str(old_value),
        "new_value": str(new_value),
        "source": source,
    }).fetchone()

    return {
        "id": row.id,
        "field": row.field,
        "old_value": row.old_value,
        "new_value": row.new_value,
        "status": row.status,
        "created_at": str(row.created_at),
    }


# =========================
# CORE ETHAN ENTRYPOINT
# =========================
@router.post("/core")
@limiter.limit("10/minute")
def advisor_core(request: Request, data: AdvisorRequest):

    def _run():
        # ✅ FIX ICI (IMPORTANT)
        user_email = get_email_from_request(request)

        if not user_email:
            raise HTTPException(status_code=401, detail="User not authenticated")

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
                metadata={"endpoint": "advisor_core", "chars": len(message)},
            )

            capture_event(
                conn,
                ETHAN_USED,
                user_id=user_id,
                email=user_email,
                properties={"endpoint": "advisor_core", "plan": plan},
            )

        result = run_ethan_chat(
            user_email,
            message,
            bypass_cache=data.bypass_cache
        )

        return validate_ethan_frontend_contract({
            "analysis": result.get("analysis", ""),
            "metadata": {
                **(result.get("metadata") or {}),
                "mode": result.get("mode", "chat"),
                "system": result.get("system", "ETHAN_CORE_V4"),
            },
        })

    return safe_execute(_run, module_name="ADVISOR_CORE")
