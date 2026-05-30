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
from advisor.ethan.memory_engine import extract_context_signals
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


@router.post("/core")
@limiter.limit("10/minute")
def advisor_core(request: Request, data: AdvisorRequest):

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
                metadata={"endpoint": "advisor_core", "chars": len(message)},
            )
            capture_event(conn, ETHAN_USED, user_id=user_id, email=user_email, properties={"endpoint": "advisor_core", "plan": plan})

        result = run_ethan_chat(user_email, message, bypass_cache=data.bypass_cache)

        return validate_ethan_frontend_contract({
            "analysis": result.get("analysis", ""),
            "metadata": {
                **(result.get("metadata") or {}),
                "mode": result.get("mode", "chat"),
                "system": result.get("system", "ETHAN_CORE_V4"),
            },
        })

    return safe_execute(_run, module_name="ADVISOR_CORE")


@router.post("/")
@router.post("/advisor")
def advisor_legacy_route():
    raise HTTPException(
        status_code=410,
        detail="Conversation endpoint moved to /advisor/core",
    )


# =========================
# 2. PORTFOLIO ANALYSIS (READ ONLY)
# =========================
@router.post("/advisor/portfolio")
@limiter.limit("10/minute")
def advisor_portfolio(request: Request, data: AdvisorRequest):
    raise HTTPException(
        status_code=410,
        detail="Portfolio conversation moved to /advisor/core",
    )


# =========================
# 3. AUTOPILOT ENGINE (SIMULATION SATELLITE ONLY)
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
                "autopilot_simulation_request",
                request,
                email=user_email,
                user_id=user_id,
                metadata={"endpoint": "advisor_autopilot", "chars": len(message)},
            )
            capture_event(conn, AUTOPILOT_SIMULATION_USED, user_id=user_id, email=user_email, properties={"endpoint": "advisor_autopilot", "plan": plan})

        result = portfolio_autopilot(user_email, message)

        return {
            "user": user_email,
            "system": "AUTOPILOT_SIMULATION_SATELLITE_V4",
            "mode": "SIMULATION",
            "authority": "no_decision_authority",
            "input": message,
            "result": result
        }

    return safe_execute(_run, module_name="AUTOPILOT_ENGINE")


@router.post("/profile-reconciliation/detect")
@limiter.limit("20/minute")
def detect_profile_reconciliation(request: Request, data: dict):
    def _run():
        user_email = request.state.user_email
        source_text = inspect_advisor_prompt(str(data.get("source_text") or data.get("message") or ""))
        proposals = []

        with engine.begin() as conn:
            ensure_ethan_action_tables(conn)
            ensure_profile_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            require_plan(plan, "GOLD", "ethan_profile_reconciliation")

            profile = conn.execute(text("""
                SELECT investor_profile, has_children, goals, horizon, risk_level,
                       motivation, transmission_goal, family_strategy
                FROM user_wealth_profiles
                WHERE user_id = :user_id
            """), {"user_id": user_id}).fetchone()

            signals = extract_context_signals(source_text)
            if signals.get("professional_context"):
                proposal = _insert_profile_proposal(
                    conn,
                    user_id,
                    "investor_profile",
                    _profile_value(profile, "investor_profile"),
                    signals["professional_context"],
                    "conversation",
                )
                if proposal:
                    proposals.append(proposal)

            if signals.get("family_constraint") and not bool(_profile_value(profile, "has_children")):
                proposal = _insert_profile_proposal(
                    conn,
                    user_id,
                    "has_children",
                    _profile_value(profile, "has_children"),
                    "true",
                    "conversation",
                )
                if proposal:
                    proposals.append(proposal)

        return {"status": "ok", "proposals": proposals}

    return safe_execute(_run, module_name="ETHAN_PROFILE_RECONCILIATION")


@router.get("/profile-reconciliation")
def list_profile_reconciliation(request: Request):
    def _run():
        user_email = request.state.user_email
        with engine.begin() as conn:
            ensure_ethan_action_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            require_plan(plan, "GOLD", "ethan_profile_reconciliation")
            rows = conn.execute(text("""
                SELECT id, field, old_value, new_value, source, status, created_at
                FROM ethan_profile_update_proposals
                WHERE user_id = :user_id
                  AND status = 'pending'
                ORDER BY created_at DESC
            """), {"user_id": user_id}).fetchall()

        return {
            "status": "ok",
            "proposals": [
                {
                    "id": row.id,
                    "field": row.field,
                    "old_value": row.old_value,
                    "new_value": row.new_value,
                    "source": row.source,
                    "status": row.status,
                    "created_at": str(row.created_at),
                }
                for row in rows
            ],
        }

    return safe_execute(_run, module_name="ETHAN_PROFILE_RECONCILIATION")


@router.post("/profile-reconciliation/{proposal_id}/accept")
def accept_profile_reconciliation(proposal_id: int, request: Request):
    def _run():
        user_email = request.state.user_email
        with engine.begin() as conn:
            ensure_ethan_action_tables(conn)
            ensure_profile_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            require_plan(plan, "GOLD", "ethan_profile_reconciliation")

            proposal = conn.execute(text("""
                SELECT id, field, old_value, new_value, status
                FROM ethan_profile_update_proposals
                WHERE id = :proposal_id
                  AND user_id = :user_id
                  AND status = 'pending'
            """), {"proposal_id": proposal_id, "user_id": user_id}).fetchone()

            if not proposal:
                raise HTTPException(status_code=404, detail="Proposal not found")
            if proposal.field not in ALLOWED_PROFILE_UPDATE_FIELDS:
                raise HTTPException(status_code=400, detail="Profile field not allowed")

            if proposal.field == "has_children":
                conn.execute(text("""
                    INSERT INTO user_wealth_profiles (user_id, has_children, updated_at)
                    VALUES (:user_id, :value, NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET has_children = EXCLUDED.has_children, updated_at = NOW()
                """), {"user_id": user_id, "value": str(proposal.new_value).lower() in ["true", "1", "yes", "oui"]})
            else:
                conn.execute(text(f"""
                    INSERT INTO user_wealth_profiles (user_id, {proposal.field}, updated_at)
                    VALUES (:user_id, :value, NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET {proposal.field} = EXCLUDED.{proposal.field}, updated_at = NOW()
                """), {"user_id": user_id, "value": proposal.new_value})

            conn.execute(text("""
                UPDATE ethan_profile_update_proposals
                SET status = 'accepted', resolved_at = NOW()
                WHERE id = :proposal_id AND user_id = :user_id
            """), {"proposal_id": proposal_id, "user_id": user_id})

        return {"status": "accepted", "proposal_id": proposal_id}

    return safe_execute(_run, module_name="ETHAN_PROFILE_RECONCILIATION")


@router.post("/profile-reconciliation/{proposal_id}/reject")
def reject_profile_reconciliation(proposal_id: int, request: Request):
    def _run():
        user_email = request.state.user_email
        with engine.begin() as conn:
            ensure_ethan_action_tables(conn)
            user_id, plan = get_user_plan(conn, user_email)
            require_plan(plan, "GOLD", "ethan_profile_reconciliation")
            conn.execute(text("""
                UPDATE ethan_profile_update_proposals
                SET status = 'rejected', resolved_at = NOW()
                WHERE id = :proposal_id
                  AND user_id = :user_id
                  AND status = 'pending'
            """), {"proposal_id": proposal_id, "user_id": user_id})
        return {"status": "rejected", "proposal_id": proposal_id}

    return safe_execute(_run, module_name="ETHAN_PROFILE_RECONCILIATION")


@router.get("/document-inbox")
def list_document_inbox(request: Request):
    def _run():
        user_email = request.state.user_email
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
        user_email = request.state.user_email
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
        user_email = request.state.user_email
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
            """), {"status": next_status, "document_id": document_id, "user_id": user_id})
        return {"status": next_status, "document_id": document_id}

    return safe_execute(_run, module_name="ETHAN_DOCUMENT_INBOX")


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
