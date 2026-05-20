import json
import os

from fastapi import HTTPException, Request
from sqlalchemy import text

from auth.utils import get_user_id
from product.entitlements import plan_allows


_security_schema_ready = False


def ensure_security_tables(conn):
    global _security_schema_ready
    if _security_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            email TEXT,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            ip_address TEXT,
            user_agent TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_security_audit_created
        ON security_audit_logs(created_at DESC)
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_security_audit_user_created
        ON security_audit_logs(user_id, created_at DESC)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_rate_limits (
            id SERIAL PRIMARY KEY,
            scope TEXT NOT NULL,
            identifier TEXT NOT NULL,
            window_start TIMESTAMP NOT NULL DEFAULT NOW(),
            counter INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(scope, identifier, window_start)
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_security_rate_limits_scope_identifier
        ON security_rate_limits(scope, identifier, window_start DESC)
    """))

    _security_schema_ready = True


def request_ip(request: Request | None):
    if not request or not request.client:
        return None
    forwarded = request.headers.get("x-forwarded-for") if request else None
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def log_security_event(
    conn,
    event_type: str,
    request: Request | None = None,
    email: str | None = None,
    user_id: int | None = None,
    severity: str = "info",
    metadata: dict | None = None,
):
    ensure_security_tables(conn)

    if email and user_id is None:
        try:
            user_id = get_user_id(conn, email)
        except Exception:
            user_id = None

    conn.execute(text("""
        INSERT INTO security_audit_logs (
            user_id, email, event_type, severity, ip_address, user_agent, metadata
        )
        VALUES (
            :user_id, :email, :event_type, :severity, :ip_address, :user_agent,
            CAST(:metadata AS JSONB)
        )
    """), {
        "user_id": user_id,
        "email": email,
        "event_type": event_type,
        "severity": severity,
        "ip_address": request_ip(request),
        "user_agent": request.headers.get("user-agent") if request else None,
        "metadata": json.dumps(metadata or {}),
    })


def is_security_admin(conn, email: str, request: Request | None = None):
    configured_admins = [
        item.strip().lower()
        for item in os.getenv("SECURITY_ADMIN_EMAILS", "").split(",")
        if item.strip()
    ]
    if configured_admins and email.lower() not in configured_admins:
        return False

    allowed_ips = [
        item.strip()
        for item in os.getenv("SECURITY_ADMIN_IPS", "").split(",")
        if item.strip()
    ]
    if allowed_ips and request_ip(request) not in allowed_ips:
        return False

    row = conn.execute(text("""
        SELECT users.plan AS user_plan, subscriptions.plan AS subscription_plan,
               subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.email = :email
    """), {"email": email}).fetchone()

    if not row:
        return False

    effective_plan = row.subscription_plan if row.subscription_status in ["active", "trialing", "past_due"] else row.user_plan
    return plan_allows(effective_plan, "LIBERTY")


def require_security_admin(conn, email: str, request: Request | None = None):
    if not is_security_admin(conn, email, request):
        log_security_event(
            conn,
            "admin_access_denied",
            request,
            email=email,
            severity="warning",
            metadata={"target": "security_admin"},
        )
        raise HTTPException(status_code=403, detail="Acces admin indisponible")
