from datetime import datetime

from fastapi import HTTPException, Request
from sqlalchemy import text

from product.entitlements import normalize_plan
from security.audit import ensure_security_tables, log_security_event, request_ip


PLAN_ETHAN_LIMITS = {
    "FREE": 15,
    "GOLD": 80,
    "ELITE": 200,
    "LIBERTY": 500,
    "LEGACY": 1000,
}


def _window_interval(window: str):
    allowed = {
        "minute": "1 minute",
        "hour": "1 hour",
        "day": "1 day",
    }
    return allowed.get(window, "1 hour")


def assert_rate_limit(
    conn,
    *,
    scope: str,
    identifier: str,
    limit: int,
    window: str,
    request: Request | None = None,
    email: str | None = None,
):
    ensure_security_tables(conn)
    interval = _window_interval(window)
    now = datetime.utcnow()

    current = conn.execute(text(f"""
        SELECT COALESCE(SUM(counter), 0)
        FROM security_rate_limits
        WHERE scope = :scope
          AND identifier = :identifier
          AND window_start >= NOW() - interval '{interval}'
    """), {"scope": scope, "identifier": identifier}).scalar()

    if int(current or 0) >= limit:
        log_security_event(
            conn,
            "rate_limit_exceeded",
            request,
            email=email,
            severity="warning",
            metadata={"scope": scope, "limit": limit, "window": window},
        )
        raise HTTPException(status_code=429, detail="Trop de requetes. Reessaie dans quelques instants.")

    conn.execute(text("""
        INSERT INTO security_rate_limits (scope, identifier, window_start, counter, updated_at)
        VALUES (:scope, :identifier, date_trunc(:window, NOW()), 1, NOW())
        ON CONFLICT (scope, identifier, window_start)
        DO UPDATE SET counter = security_rate_limits.counter + 1, updated_at = NOW()
    """), {
        "scope": scope,
        "identifier": identifier,
        "window": window,
    })


def assert_ip_rate_limit(conn, scope: str, limit: int, window: str, request: Request):
    assert_rate_limit(
        conn,
        scope=scope,
        identifier=request_ip(request) or "unknown",
        limit=limit,
        window=window,
        request=request,
    )


def assert_ethan_limit(conn, request: Request, email: str, plan: str):
    normalized = normalize_plan(plan)
    limit = PLAN_ETHAN_LIMITS.get(normalized, PLAN_ETHAN_LIMITS["FREE"])
    assert_rate_limit(
        conn,
        scope="ethan",
        identifier=email,
        limit=limit,
        window="hour",
        request=request,
        email=email,
    )


def suspicious_ip_count(conn, hours: int = 24):
    ensure_security_tables(conn)
    return conn.execute(text("""
        SELECT ip_address, COUNT(*) AS events
        FROM security_audit_logs
        WHERE severity IN ('warning', 'critical')
          AND ip_address IS NOT NULL
          AND created_at >= NOW() - (:hours * interval '1 hour')
        GROUP BY ip_address
        ORDER BY events DESC
        LIMIT 20
    """), {"hours": hours}).fetchall()
