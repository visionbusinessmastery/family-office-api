import csv
import io
import json
import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import text

from auth.email_service import FRONTEND_URL
from auth.utils import get_current_user, get_user_id, verify_password
from database import engine
from privacy.region_engine import detect_privacy_region
from security.abuse_engine import assert_rate_limit
from security.audit import log_security_event as log_security_audit
from analytics.analytics_events import EXPORT_GENERATED
from analytics.posthog_service import capture_event


router = APIRouter()
profile_router = APIRouter()
_privacy_schema_ready = False

POLICY_VERSION = "2026-05-white-rock-v1"

CONSENT_KEYS = [
    "terms_accepted",
    "privacy_policy_accepted",
    "ai_processing_accepted",
    "marketing_emails_accepted",
    "analytics_accepted",
    "personalized_opportunities_accepted",
    "weekly_reports_accepted",
    "third_party_data_processing_accepted",
]

EMAIL_KEYS = [
    "weekly_reports",
    "marketing",
    "product_updates",
    "opportunities",
    "challenges",
    "onboarding",
    "founder_program",
]

COOKIE_KEYS = ["essential", "analytics", "marketing", "personalization"]


def _send_privacy_email(to_email: str, subject: str, html: str):
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("FROM_EMAIL", "WHITE ROCK <noreply@vision-business.com>")
    if not api_key:
        return False

    try:
        import requests

        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": html,
            },
            timeout=10,
        )
        return response.status_code < 400
    except Exception:
        return False


def ensure_privacy_tables(conn):
    global _privacy_schema_ready
    if _privacy_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_consents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            consent_key TEXT NOT NULL,
            accepted BOOLEAN NOT NULL DEFAULT FALSE,
            policy_version TEXT,
            ip_address TEXT,
            country TEXT,
            region TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_user_consents_user_key_created
        ON user_consents(user_id, consent_key, created_at DESC)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS privacy_audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            event_type TEXT NOT NULL,
            metadata JSONB,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_privacy_audit_user_created
        ON privacy_audit_logs(user_id, created_at DESC)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_data_exports (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            format TEXT NOT NULL DEFAULT 'json',
            status TEXT NOT NULL DEFAULT 'ready',
            token TEXT NOT NULL UNIQUE,
            payload JSONB,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            downloaded_at TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_deletion_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            token TEXT NOT NULL UNIQUE,
            requested_at TIMESTAMP DEFAULT NOW(),
            scheduled_for TIMESTAMP NOT NULL,
            canceled_at TIMESTAMP,
            completed_at TIMESTAMP,
            reason TEXT
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS cookie_consents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            anonymous_id TEXT,
            preferences JSONB NOT NULL,
            region TEXT,
            policy_version TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS privacy_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            email_preferences JSONB NOT NULL DEFAULT '{}',
            ai_preferences JSONB NOT NULL DEFAULT '{}',
            cookie_preferences JSONB NOT NULL DEFAULT '{}',
            security_preferences JSONB NOT NULL DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    _privacy_schema_ready = True


def _request_meta(request: Request):
    country = request.headers.get("CF-IPCountry") or request.headers.get("X-Country")
    province = request.headers.get("X-Region") or request.headers.get("X-Province")
    region = detect_privacy_region(country, province)

    return {
        "ip_address": request.client.host if request.client else None,
        "country": country,
        "region": region["region"],
        "user_agent": request.headers.get("user-agent"),
        "frameworks": region["frameworks"],
    }


def log_privacy_event(conn, user_id: int | None, event_type: str, metadata: dict | None, request: Request | None = None):
    ensure_privacy_tables(conn)
    meta = {}
    if request:
        meta = _request_meta(request)

    conn.execute(text("""
        INSERT INTO privacy_audit_logs (user_id, event_type, metadata, ip_address, user_agent)
        VALUES (:user_id, :event_type, CAST(:metadata AS JSONB), :ip_address, :user_agent)
    """), {
        "user_id": user_id,
        "event_type": event_type,
        "metadata": json.dumps(metadata or {}),
        "ip_address": meta.get("ip_address"),
        "user_agent": meta.get("user_agent"),
    })


def record_consents(conn, user_id: int, consents: dict, request: Request | None = None):
    ensure_privacy_tables(conn)
    meta = _request_meta(request) if request else {}

    for key in CONSENT_KEYS:
        if key not in consents:
            continue

        conn.execute(text("""
            INSERT INTO user_consents (
                user_id, consent_key, accepted, policy_version,
                ip_address, country, region, user_agent
            )
            VALUES (
                :user_id, :consent_key, :accepted, :policy_version,
                :ip_address, :country, :region, :user_agent
            )
        """), {
            "user_id": user_id,
            "consent_key": key,
            "accepted": bool(consents.get(key)),
            "policy_version": POLICY_VERSION,
            "ip_address": meta.get("ip_address"),
            "country": meta.get("country"),
            "region": meta.get("region"),
            "user_agent": meta.get("user_agent"),
        })

    log_privacy_event(conn, user_id, "consent_updated", {"keys": list(consents.keys())}, request)

    email_preferences = {
        "weekly_reports": bool(consents.get("weekly_reports_accepted")),
        "marketing": bool(consents.get("marketing_emails_accepted")),
        "product_updates": True,
        "opportunities": bool(consents.get("personalized_opportunities_accepted")),
        "challenges": True,
        "onboarding": True,
        "founder_program": bool(consents.get("marketing_emails_accepted")),
    }
    ai_preferences = {
        "ai_processing": bool(consents.get("ai_processing_accepted")),
        "personalized_opportunities": bool(consents.get("personalized_opportunities_accepted")),
        "third_party_data_processing": bool(consents.get("third_party_data_processing_accepted")),
    }

    conn.execute(text("""
        INSERT INTO privacy_preferences (
            user_id, email_preferences, ai_preferences, cookie_preferences,
            security_preferences, updated_at
        )
        VALUES (
            :user_id, CAST(:email_preferences AS JSONB), CAST(:ai_preferences AS JSONB),
            CAST(:cookie_preferences AS JSONB), CAST(:security_preferences AS JSONB), NOW()
        )
        ON CONFLICT (user_id)
        DO UPDATE SET
            email_preferences = privacy_preferences.email_preferences || EXCLUDED.email_preferences,
            ai_preferences = privacy_preferences.ai_preferences || EXCLUDED.ai_preferences,
            updated_at = NOW()
    """), {
        "user_id": user_id,
        "email_preferences": json.dumps(email_preferences),
        "ai_preferences": json.dumps(ai_preferences),
        "cookie_preferences": json.dumps({"analytics": bool(consents.get("analytics_accepted"))}),
        "security_preferences": json.dumps({}),
    })


def latest_consents(conn, user_id: int):
    rows = conn.execute(text("""
        SELECT DISTINCT ON (consent_key)
            consent_key, accepted, policy_version, country, region, user_agent, created_at
        FROM user_consents
        WHERE user_id = :user_id
        ORDER BY consent_key, created_at DESC
    """), {"user_id": user_id}).fetchall()

    return {
        row.consent_key: {
            "accepted": bool(row.accepted),
            "policy_version": row.policy_version,
            "country": row.country,
            "region": row.region,
            "user_agent": row.user_agent,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    }


def _fetch_rows(conn, query: str, params: dict):
    try:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result.fetchall()]
    except Exception:
        return []


def build_export_payload(conn, user_id: int, email: str):
    params = {"user_id": user_id, "email": email}
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "policy_version": POLICY_VERSION,
        "user": _fetch_rows(conn, "SELECT id, email, plan, profile_completed, created_at FROM users WHERE id = :user_id", params),
        "profile": _fetch_rows(conn, "SELECT * FROM user_wealth_profiles WHERE user_id = :user_id", params),
        "finance": _fetch_rows(conn, "SELECT * FROM finance_items WHERE user_id = :user_id", params),
        "portfolio": _fetch_rows(conn, "SELECT * FROM portfolio WHERE user_id = :user_id", params),
        "real_estate": _fetch_rows(conn, "SELECT * FROM real_estate_assets WHERE user_id = :user_id", params),
        "yield_assets": _fetch_rows(conn, "SELECT * FROM yield_assets WHERE user_id = :user_id", params),
        "venture_assets": _fetch_rows(conn, "SELECT * FROM venture_assets WHERE user_id = :user_id", params),
        "notifications": _fetch_rows(conn, "SELECT * FROM notifications WHERE user_id = :user_id", params),
        "progression": _fetch_rows(conn, "SELECT * FROM progression_profiles WHERE user_id = :user_id", params),
        "subscriptions": _fetch_rows(conn, "SELECT plan, status, current_period_end, created_at, updated_at FROM subscriptions WHERE user_id = :user_id", params),
        "billing_invoices": _fetch_rows(conn, "SELECT stripe_invoice_id, amount_due, amount_paid, currency, status, created_at FROM billing_invoices WHERE user_id = :user_id", params),
        "oauth_accounts": _fetch_rows(conn, "SELECT provider, provider_email, provider_avatar, created_at, updated_at FROM oauth_accounts WHERE user_id = :user_id", params),
        "ethan_memory": _fetch_rows(conn, "SELECT strategic_summary, session_summary, last_topic, updated_at FROM ethan_memory WHERE user_id = :user_id", params),
        "ethan_usage": _fetch_rows(conn, "SELECT task_type, complexity, model, estimated_cost_usd, created_at FROM ethan_usage_events WHERE user_id = :user_id", params),
        "legacy": {
            "vault": _fetch_rows(conn, "SELECT * FROM legacy_family_vault WHERE user_id = :user_id", params),
            "heirs": _fetch_rows(conn, "SELECT * FROM legacy_heirs WHERE user_id = :user_id", params),
            "governance": _fetch_rows(conn, "SELECT * FROM legacy_governance_rules WHERE user_id = :user_id", params),
            "metrics": _fetch_rows(conn, "SELECT * FROM legacy_metrics WHERE user_id = :user_id", params),
        },
        "privacy": {
            "consents": latest_consents(conn, user_id),
            "preferences": _fetch_rows(conn, "SELECT * FROM privacy_preferences WHERE user_id = :user_id", params),
            "audit_logs": _fetch_rows(conn, "SELECT event_type, metadata, created_at FROM privacy_audit_logs WHERE user_id = :user_id", params),
        },
    }


def _payload_to_csv(payload: dict):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "count"])
    for key, value in payload.items():
        if isinstance(value, list):
            writer.writerow([key, len(value)])
        elif isinstance(value, dict):
            writer.writerow([key, len(value)])
        else:
            writer.writerow([key, value])
    return output.getvalue()


def _payload_to_pdf_text(payload: dict):
    lines = [
        "WHITE ROCK - Export donnees personnelles",
        f"Genere le {payload.get('generated_at')}",
        "",
        "Resume des sections exportees:",
    ]
    for key, value in payload.items():
        if isinstance(value, list):
            lines.append(f"- {key}: {len(value)} element(s)")
        elif isinstance(value, dict):
            lines.append(f"- {key}: {len(value)} sous-section(s)")
    return "\n".join(lines)


@router.get("/region")
def privacy_region(request: Request):
    meta = _request_meta(request)
    return {"policy_version": POLICY_VERSION, **detect_privacy_region(meta.get("country"), None)}


@router.get("/center")
def privacy_center(request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        consents = latest_consents(conn, user_id)
        history = _fetch_rows(conn, """
            SELECT consent_key, accepted, policy_version, region, created_at
            FROM user_consents
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 50
        """, {"user_id": user_id})
        preferences = _fetch_rows(conn, "SELECT * FROM privacy_preferences WHERE user_id = :user_id", {"user_id": user_id})
        deletion = _fetch_rows(conn, """
            SELECT status, requested_at, scheduled_for, canceled_at, completed_at
            FROM user_deletion_requests
            WHERE user_id = :user_id
            ORDER BY requested_at DESC
            LIMIT 1
        """, {"user_id": user_id})

        counts = {
            "portfolio": len(_fetch_rows(conn, "SELECT id FROM portfolio WHERE user_id = :user_id", {"user_id": user_id})),
            "real_estate": len(_fetch_rows(conn, "SELECT id FROM real_estate_assets WHERE user_id = :user_id", {"user_id": user_id})),
            "ethan_memory": len(_fetch_rows(conn, "SELECT id FROM ethan_memory WHERE user_id = :user_id", {"user_id": user_id})),
            "notifications": len(_fetch_rows(conn, "SELECT id FROM notifications WHERE user_id = :user_id", {"user_id": user_id})),
            "legacy": len(_fetch_rows(conn, "SELECT id FROM legacy_family_vault WHERE user_id = :user_id", {"user_id": user_id})),
            "oauth_accounts": len(_fetch_rows(conn, "SELECT id FROM oauth_accounts WHERE user_id = :user_id", {"user_id": user_id})),
        }
        log_privacy_event(conn, user_id, "privacy_center_opened", {}, request)

    return {
        "policy_version": POLICY_VERSION,
        "data_summary": counts,
        "consents": consents,
        "consent_history": history,
        "preferences": preferences[0] if preferences else {},
        "deletion_request": deletion[0] if deletion else None,
        "ai_disclosure": {
            "provider": "OpenAI",
            "purpose": "Le moteur IA analyse ton contexte patrimonial pour formuler des explications, priorites et opportunites.",
            "training": "Les donnees envoyees au moteur IA ne sont pas destinees a entrainer un modele public de WHITE ROCK.",
            "retention": "La memoire IA est compressee et peut etre supprimee sur demande.",
            "human_note": "Le moteur IA ne remplace pas un conseil legal, fiscal ou financier reglemente.",
        },
        "legal_links": {
            "privacy_policy": f"{FRONTEND_URL}/privacy-center#policy",
            "terms": f"{FRONTEND_URL}/privacy-center#terms",
        },
    }


@router.post("/consents")
def update_consents(data: dict, request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        record_consents(conn, user_id, data, request)
    return {"status": "ok", "consents": data}


@router.put("/consents")
def put_consents(data: dict, request: Request, email: str = Depends(get_current_user)):
    return update_consents(data, request, email)


@router.put("/preferences")
def update_preferences(data: dict, request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        conn.execute(text("""
            INSERT INTO privacy_preferences (
                user_id, email_preferences, ai_preferences, cookie_preferences,
                security_preferences, updated_at
            )
            VALUES (
                :user_id, CAST(:email_preferences AS JSONB), CAST(:ai_preferences AS JSONB),
                CAST(:cookie_preferences AS JSONB), CAST(:security_preferences AS JSONB), NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                email_preferences = EXCLUDED.email_preferences,
                ai_preferences = EXCLUDED.ai_preferences,
                cookie_preferences = EXCLUDED.cookie_preferences,
                security_preferences = EXCLUDED.security_preferences,
                updated_at = NOW()
        """), {
            "user_id": user_id,
            "email_preferences": json.dumps(data.get("email_preferences") or {}),
            "ai_preferences": json.dumps(data.get("ai_preferences") or {}),
            "cookie_preferences": json.dumps(data.get("cookie_preferences") or {}),
            "security_preferences": json.dumps(data.get("security_preferences") or {}),
        })
        log_privacy_event(conn, user_id, "privacy_preferences_updated", data, request)

    return {"status": "ok"}


@router.put("/email-preferences")
def update_email_preferences(data: dict, request: Request, email: str = Depends(get_current_user)):
    return update_preferences({"email_preferences": data}, request, email)


@router.post("/cookie-consent")
def cookie_consent(data: dict, request: Request):
    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        email = getattr(request.state, "user_email", None)
        user_id = None
        try:
            user_id = get_user_id(conn, email) if email and email != "anonymous" else None
        except Exception:
            user_id = None
        meta = _request_meta(request)
        preferences = {
            key: bool((data.get("preferences") or {}).get(key))
            for key in COOKIE_KEYS
        }
        preferences["essential"] = True

        conn.execute(text("""
            INSERT INTO cookie_consents (
                user_id, anonymous_id, preferences, region, policy_version,
                ip_address, user_agent
            )
            VALUES (
                :user_id, :anonymous_id, CAST(:preferences AS JSONB), :region, :policy_version,
                :ip_address, :user_agent
            )
        """), {
            "user_id": user_id,
            "anonymous_id": data.get("anonymous_id"),
            "preferences": json.dumps(preferences),
            "region": meta.get("region"),
            "policy_version": POLICY_VERSION,
            "ip_address": meta.get("ip_address"),
            "user_agent": meta.get("user_agent"),
        })
        log_privacy_event(conn, user_id, "cookie_consent_updated", preferences, request)
    return {"status": "ok", "preferences": preferences}


@router.post("/export")
def request_export(data: dict, request: Request, email: str = Depends(get_current_user)):
    fmt = str(data.get("format") or "json").lower()
    if fmt not in ["json", "csv", "pdf"]:
        raise HTTPException(status_code=400, detail="Format export invalide")

    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        assert_rate_limit(
            conn,
            scope="privacy_export",
            identifier=email,
            limit=2,
            window="day",
            request=request,
            email=email,
        )

        payload = build_export_payload(conn, user_id, email)
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)
        conn.execute(text("""
            INSERT INTO user_data_exports (user_id, format, status, token, payload, expires_at)
            VALUES (:user_id, :format, 'ready', :token, CAST(:payload AS JSONB), :expires_at)
        """), {
            "user_id": user_id,
            "format": fmt,
            "token": token,
            "payload": json.dumps(payload, default=str),
            "expires_at": expires_at,
        })
        log_privacy_event(conn, user_id, "data_export_requested", {"format": fmt}, request)
        log_security_audit(conn, "privacy_export_requested", request, email=email, user_id=user_id, metadata={"format": fmt})
        capture_event(conn, EXPORT_GENERATED, user_id=user_id, email=email, properties={"format": fmt})

    return {
        "status": "ready",
        "format": fmt,
        "expires_at": expires_at.isoformat(),
        "download_url": f"/privacy/export/{token}",
    }


@router.get("/export/{token}")
def download_export(token: str, request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        user_id = get_user_id(conn, email)
        row = conn.execute(text("""
            SELECT format, payload, expires_at
            FROM user_data_exports
            WHERE token = :token AND user_id = :user_id
        """), {"token": token, "user_id": user_id}).fetchone()

        if not row or row.expires_at < datetime.utcnow():
            raise HTTPException(status_code=404, detail="Export introuvable ou expire")

        conn.execute(text("""
            UPDATE user_data_exports SET downloaded_at = NOW() WHERE token = :token
        """), {"token": token})
        log_privacy_event(conn, user_id, "data_export_downloaded", {"format": row.format}, request)

    payload = row.payload if isinstance(row.payload, dict) else json.loads(row.payload)
    if row.format == "csv":
        return Response(_payload_to_csv(payload), media_type="text/csv")
    if row.format == "pdf":
        return Response(_payload_to_pdf_text(payload), media_type="application/pdf")
    return Response(json.dumps(payload, default=str, indent=2), media_type="application/json")


@router.post("/delete-account")
def request_delete_account(data: dict, request: Request, email: str = Depends(get_current_user)):
    password = data.get("password")
    if not password:
        raise HTTPException(status_code=400, detail="Mot de passe requis")

    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        user = conn.execute(text("""
            SELECT id, email, password_hash FROM users WHERE email = :email
        """), {"email": email}).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.password_hash and not verify_password(password, user.password_hash):
            raise HTTPException(status_code=400, detail="Mot de passe incorrect")

        token = secrets.token_urlsafe(32)
        scheduled_for = datetime.utcnow() + timedelta(days=7)
        conn.execute(text("""
            INSERT INTO user_deletion_requests (user_id, status, token, scheduled_for, reason)
            VALUES (:user_id, 'pending', :token, :scheduled_for, :reason)
        """), {
            "user_id": user.id,
            "token": token,
            "scheduled_for": scheduled_for,
            "reason": data.get("reason"),
        })
        log_privacy_event(conn, user.id, "account_deletion_requested", {"scheduled_for": scheduled_for.isoformat()}, request)

    confirm_url = f"{FRONTEND_URL}/privacy-center?confirm_delete={token}"
    _send_privacy_email(
        user.email,
        "Confirmation de suppression WHITE ROCK",
        f"""
        <div style="font-family:Arial,sans-serif;line-height:1.6;color:#111827">
          <h1>Confirmation de suppression</h1>
          <p>Nous avons recu une demande de suppression de compte WHITE ROCK.</p>
          <p>Cette action sera executee apres un delai de securite de 7 jours uniquement apres confirmation.</p>
          <p><a href="{confirm_url}" style="display:inline-block;background:#3fa9f5;color:white;padding:12px 18px;border-radius:10px;text-decoration:none">Confirmer la suppression</a></p>
          <p>Si tu n'es pas a l'origine de cette demande, ignore cet email et annule la demande depuis ton Privacy Center.</p>
        </div>
        """,
    )

    return {
        "status": "pending",
        "scheduled_for": scheduled_for.isoformat(),
        "cancel_url": "/privacy/delete-account/cancel",
    }


@router.post("/delete-account/confirm/{token}")
def confirm_delete_account(token: str, request: Request):
    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        row = conn.execute(text("""
            UPDATE user_deletion_requests
            SET status = 'confirmed'
            WHERE token = :token AND status = 'pending'
            RETURNING user_id, scheduled_for
        """), {"token": token}).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Demande introuvable ou deja traitee")

        log_privacy_event(conn, row.user_id, "account_deletion_confirmed", {"scheduled_for": row.scheduled_for.isoformat()}, request)

    return {"status": "confirmed", "scheduled_for": row.scheduled_for.isoformat()}


@router.post("/delete-account/cancel")
def cancel_delete_account(request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute(text("""
            UPDATE user_deletion_requests
            SET status = 'canceled', canceled_at = NOW()
            WHERE user_id = :user_id AND status = 'pending'
        """), {"user_id": user_id})
        log_privacy_event(conn, user_id, "account_deletion_canceled", {}, request)
    return {"status": "canceled"}


@router.get("/audit-logs")
def audit_logs(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_privacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        rows = _fetch_rows(conn, """
            SELECT event_type, metadata, created_at
            FROM privacy_audit_logs
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 100
        """, {"user_id": user_id})
    return {"logs": rows}


@router.post("/retention/run")
def run_retention(email: str = Depends(get_current_user)):
    if not email.endswith("@vision-business.com"):
        raise HTTPException(status_code=403, detail="Admin only")

    from privacy.retention_engine import run_retention_purge

    with engine.begin() as conn:
        results = run_retention_purge(conn)
        log_privacy_event(conn, None, "retention_purge_run", results, None)
    return results


@profile_router.post("/export")
def profile_export(data: dict, request: Request, email: str = Depends(get_current_user)):
    return request_export(data, request, email)


@profile_router.post("/delete-account")
def profile_delete_account(data: dict, request: Request, email: str = Depends(get_current_user)):
    return request_delete_account(data, request, email)


@profile_router.post("/delete-account/cancel")
def profile_cancel_delete_account(request: Request, email: str = Depends(get_current_user)):
    return cancel_delete_account(request, email)
