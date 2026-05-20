from fastapi import APIRouter, Depends, Request
from sqlalchemy import text

from auth.utils import get_current_user
from database import engine
from security.abuse_engine import suspicious_ip_count
from security.audit import ensure_security_tables, log_security_event, require_security_admin


router = APIRouter()


@router.get("/admin/summary")
def security_admin_summary(request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_security_tables(conn)
        require_security_admin(conn, email, request)

        by_event = conn.execute(text("""
            SELECT event_type, severity, COUNT(*) AS count
            FROM security_audit_logs
            WHERE created_at >= NOW() - interval '7 days'
            GROUP BY event_type, severity
            ORDER BY count DESC
            LIMIT 30
        """)).fetchall()

        recent = conn.execute(text("""
            SELECT event_type, severity, email, ip_address, metadata, created_at
            FROM security_audit_logs
            ORDER BY created_at DESC
            LIMIT 50
        """)).fetchall()

        rate_limits = conn.execute(text("""
            SELECT scope, COUNT(DISTINCT identifier) AS actors, SUM(counter) AS requests
            FROM security_rate_limits
            WHERE window_start >= NOW() - interval '24 hours'
            GROUP BY scope
            ORDER BY requests DESC
        """)).fetchall()

        suspicious_ips = suspicious_ip_count(conn)
        log_security_event(conn, "security_dashboard_opened", request, email=email)

    return {
        "window": "7d",
        "events": [
            {
                "event_type": row.event_type,
                "severity": row.severity,
                "count": int(row.count or 0),
            }
            for row in by_event
        ],
        "recent": [
            {
                "event_type": row.event_type,
                "severity": row.severity,
                "email": row.email,
                "ip_address": row.ip_address,
                "metadata": row.metadata,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in recent
        ],
        "rate_limits": [
            {
                "scope": row.scope,
                "actors": int(row.actors or 0),
                "requests": int(row.requests or 0),
            }
            for row in rate_limits
        ],
        "suspicious_ips": [
            {"ip_address": row.ip_address, "events": int(row.events or 0)}
            for row in suspicious_ips
        ],
    }
