import json
import os
import time

import requests
from sqlalchemy import text


_analytics_schema_ready = False


def ensure_analytics_tables(conn):
    global _analytics_schema_ready
    if _analytics_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS analytics_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            email TEXT,
            event_name TEXT NOT NULL,
            properties JSONB,
            provider TEXT DEFAULT 'posthog',
            dispatched BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_analytics_events_created
        ON analytics_events(created_at DESC)
    """))

    _analytics_schema_ready = True


def analytics_consent_enabled(conn, user_id: int | None):
    if not user_id:
        return False
    try:
        row = conn.execute(text("""
            SELECT accepted
            FROM user_consents
            WHERE user_id = :user_id AND consent_key = 'analytics_accepted'
            ORDER BY created_at DESC
            LIMIT 1
        """), {"user_id": user_id}).fetchone()
        return bool(row and row.accepted)
    except Exception:
        return False


def capture_event(conn, event_name: str, user_id: int | None = None, email: str | None = None, properties: dict | None = None):
    ensure_analytics_tables(conn)
    if not analytics_consent_enabled(conn, user_id):
        return False

    payload = {
        "user_id": user_id,
        "email": email,
        "event_name": event_name,
        "properties": json.dumps(properties or {}),
    }
    conn.execute(text("""
        INSERT INTO analytics_events (user_id, email, event_name, properties)
        VALUES (:user_id, :email, :event_name, CAST(:properties AS JSONB))
    """), payload)

    api_key = os.getenv("POSTHOG_API_KEY")
    host = os.getenv("POSTHOG_HOST", "https://app.posthog.com").rstrip("/")
    if not api_key:
        return False

    try:
        response = requests.post(
            f"{host}/capture/",
            json={
                "api_key": api_key,
                "event": event_name,
                "distinct_id": str(user_id or email or "anonymous"),
                "properties": {
                    **(properties or {}),
                    "$lib": "white-rock-backend",
                    "captured_at": int(time.time()),
                },
            },
            timeout=3,
        )
        dispatched = response.status_code < 400
        if dispatched:
            conn.execute(text("""
                UPDATE analytics_events
                SET dispatched = TRUE
                WHERE id = (
                    SELECT id FROM analytics_events
                    WHERE user_id IS NOT DISTINCT FROM :user_id
                      AND event_name = :event_name
                    ORDER BY created_at DESC
                    LIMIT 1
                )
            """), {"user_id": user_id, "event_name": event_name})
        return dispatched
    except Exception:
        return False
