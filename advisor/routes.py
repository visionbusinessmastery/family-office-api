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

@router.get("/context-summary")
def advisor_context_summary(request: Request):
    def _run():
        user_email = get_email_from_request(request)

        if not user_email:
            raise HTTPException(status_code=401, detail="User not authenticated")

        with engine.begin() as conn:
            user_id, plan = get_user_plan(conn, user_email)

            context = {
                "user_id": user_id,
                "plan": plan,
            }

            # 👇 tu branches ici ton engine existant
            memory = get_memory(conn, user_id)
            life_context = build_life_context(conn, user_id, memory)
            signals = extract_context_signals(context)

            summary = summarize_context_profile({
                "memory": memory,
                "life_context": life_context,
                "signals": signals,
                "plan": plan,
                "user_id": user_id,
            })

            return summary

    return safe_execute(_run, module_name="ADVISOR_CONTEXT_SUMMARY")

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


@router.get("/document-inbox")
def list_document_inbox(request: Request):
    def _run():
        user_email = get_email_from_request(request)

        if not user_email:
            raise HTTPException(status_code=401, detail="User not authenticated")

        with engine.begin() as conn:
            ensure_ethan_action_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            require_plan(plan, "ELITE", "patrimonial_document_inbox")
            rows = conn.execute(text("""
                SELECT id, filename, document_type, extracted_data, proposed_updates, status, created_at
                FROM ethan_document_inbox
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 50
            """), {"user_id": user_id}).fetchall()

        return {
            "status": "ok",
            "documents": [
                {
                    "id": row.id,
                    "filename": row.filename,
                    "document_type": row.document_type,
                    "extracted_data": row.extracted_data or {},
                    "proposed_updates": row.proposed_updates or [],
                    "status": row.status,
                    "created_at": str(row.created_at),
                }
                for row in rows
            ],
        }

    return safe_execute(_run, module_name="ETHAN_DOCUMENT_INBOX")


@router.post("/document-inbox")
@limiter.limit("10/minute")
def create_document_inbox_item(request: Request, data: dict):
    def _run():
        user_email = get_email_from_request(request)

        if not user_email:
            raise HTTPException(status_code=401, detail="User not authenticated")

        with engine.begin() as conn:
            ensure_ethan_action_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            require_plan(plan, "ELITE", "patrimonial_document_inbox")
            row = conn.execute(text("""
                INSERT INTO ethan_document_inbox (
                    user_id, filename, document_type, extracted_data, proposed_updates
                )
                VALUES (
                    :user_id, :filename, :document_type,
                    CAST(:extracted_data AS JSONB), CAST(:proposed_updates AS JSONB)
                )
                RETURNING id, filename, document_type, extracted_data, proposed_updates, status, created_at
            """), {
                "user_id": user_id,
                "filename": str(data.get("filename") or "Document"),
                "document_type": str(data.get("document_type") or "unknown"),
                "extracted_data": __import__("json").dumps(data.get("extracted_data") or {}),
                "proposed_updates": __import__("json").dumps(data.get("proposed_updates") or []),
            }).fetchone()

        return {
            "status": "pending",
            "document": {
                "id": row.id,
                "filename": row.filename,
                "document_type": row.document_type,
                "extracted_data": row.extracted_data or {},
                "proposed_updates": row.proposed_updates or [],
                "status": row.status,
                "created_at": str(row.created_at),
            },
        }

    return safe_execute(_run, module_name="ETHAN_DOCUMENT_INBOX")


@router.post("/document-inbox/{document_id}/resolve")
def resolve_document_inbox_item(document_id: int, request: Request, data: dict):
    def _run():
        user_email = get_email_from_request(request)

        if not user_email:
            raise HTTPException(status_code=401, detail="User not authenticated")

        next_status = "accepted" if bool(data.get("accept")) else "rejected"
        with engine.begin() as conn:
            ensure_ethan_action_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            require_plan(plan, "ELITE", "patrimonial_document_inbox")
            conn.execute(text("""
                UPDATE ethan_document_inbox
                SET status = :status, resolved_at = NOW()
                WHERE id = :document_id
                  AND user_id = :user_id
                  AND status = 'pending'
            """), {
                "status": next_status,
                "document_id": document_id,
                "user_id": user_id,
            })

        return {"status": next_status, "document_id": document_id}

    return safe_execute(_run, module_name="ETHAN_DOCUMENT_INBOX")
