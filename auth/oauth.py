import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy import text

from analytics.posthog_service import capture_event
from auth.utils import create_token, get_current_user, get_user_id
from database import engine
from feature_flags.engine import ensure_feature_flags_table, is_feature_enabled
from privacy.routes import record_consents
from security.audit import ensure_security_tables, log_security_event, require_security_admin


router = APIRouter()
_oauth_schema_ready = False

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://vision-business.com").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "https://family-office-api-n4sv.onrender.com").rstrip("/")
OAUTH_FLOW_TTL_MINUTES = 10
OAUTH_SESSION_TTL_MINUTES = 5

PROVIDERS = {
    "google": {
        "label": "Google",
        "flag": "oauth_google_enabled",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "jwks_url": "https://www.googleapis.com/oauth2/v3/certs",
        "issuer": "https://accounts.google.com",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "scopes": ["openid", "email", "profile"],
    },
    "apple": {
        "label": "Apple",
        "flag": "oauth_apple_enabled",
        "auth_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "jwks_url": "https://appleid.apple.com/auth/keys",
        "issuer": "https://appleid.apple.com",
        "client_id_env": "APPLE_CLIENT_ID",
        "client_secret_env": "APPLE_CLIENT_SECRET",
        "scopes": ["email", "name"],
    },
    "microsoft": {
        "label": "Microsoft",
        "flag": "oauth_microsoft_enabled",
        "coming_soon": True,
    },
    "linkedin": {
        "label": "LinkedIn",
        "flag": "oauth_linkedin_enabled",
        "coming_soon": True,
    },
}


def ensure_oauth_tables(conn):
    global _oauth_schema_ready
    if _oauth_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS oauth_accounts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_user_id TEXT NOT NULL,
            provider_email TEXT,
            provider_avatar TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(provider, provider_user_id)
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user_provider
        ON oauth_accounts(user_id, provider)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS oauth_flows (
            id SERIAL PRIMARY KEY,
            provider TEXT NOT NULL,
            state TEXT NOT NULL UNIQUE,
            code_verifier TEXT NOT NULL,
            nonce TEXT NOT NULL,
            redirect_path TEXT NOT NULL DEFAULT '/dashboard',
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP NOT NULL,
            consumed_at TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS oauth_login_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT NOW(),
            expires_at TIMESTAMP NOT NULL,
            consumed_at TIMESTAMP
        )
    """))

    _oauth_schema_ready = True


def _request_ip(request: Request):
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _provider_config(provider: str):
    provider = str(provider or "").lower()
    config = PROVIDERS.get(provider)
    if not config or config.get("coming_soon"):
        raise HTTPException(status_code=404, detail="Provider OAuth indisponible")
    return provider, config


def _redirect_path(path: str | None):
    value = str(path or "/dashboard")
    if not value.startswith("/") or value.startswith("//"):
        return "/dashboard"
    if value.startswith("/auth/callback"):
        return "/dashboard"
    return value[:200]


def _code_challenge(verifier: str):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _oauth_redirect_uri(provider: str):
    return f"{BACKEND_URL}/auth/oauth/{provider}/callback"


def _client_secret(provider: str, config: dict):
    if provider != "apple":
        return os.getenv(config["client_secret_env"])

    explicit = os.getenv("APPLE_CLIENT_SECRET")
    if explicit:
        return explicit

    private_key = os.getenv("APPLE_PRIVATE_KEY", "").replace("\\n", "\n")
    team_id = os.getenv("APPLE_TEAM_ID")
    key_id = os.getenv("APPLE_KEY_ID")
    client_id = os.getenv("APPLE_CLIENT_ID")
    if not private_key or not team_id or not key_id or not client_id:
        return None

    now = datetime.utcnow()
    return jwt.encode(
        {
            "iss": team_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=30)).timestamp()),
            "aud": "https://appleid.apple.com",
            "sub": client_id,
        },
        private_key,
        algorithm="ES256",
        headers={"kid": key_id},
    )


def _provider_runtime_ready(provider: str, config: dict):
    if config.get("coming_soon"):
        return False
    if not os.getenv(config.get("client_id_env", "")):
        return False
    if provider == "apple":
        return bool(
            os.getenv("APPLE_CLIENT_SECRET")
            or (
                os.getenv("APPLE_TEAM_ID")
                and os.getenv("APPLE_KEY_ID")
                and os.getenv("APPLE_PRIVATE_KEY")
            )
        )
    return bool(os.getenv(config.get("client_secret_env", "")))


def _verify_id_token(id_token: str, provider: str, config: dict, nonce: str):
    try:
        header = jwt.get_unverified_header(id_token)
        jwks = requests.get(config["jwks_url"], timeout=5).json().get("keys", [])
        key = next((item for item in jwks if item.get("kid") == header.get("kid")), None)
        if not key:
            raise HTTPException(status_code=400, detail="Cle OAuth invalide")
        payload = jwt.decode(
            id_token,
            key,
            algorithms=[header.get("alg", "RS256")],
            audience=os.getenv(config["client_id_env"]),
            issuer=config["issuer"],
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Identite OAuth invalide")

    if payload.get("nonce") and payload.get("nonce") != nonce:
        raise HTTPException(status_code=400, detail="Nonce OAuth invalide")
    if not payload.get("email"):
        raise HTTPException(status_code=400, detail="Email OAuth manquant")

    return {
        "provider_user_id": payload.get("sub"),
        "email": str(payload.get("email")).lower(),
        "email_verified": bool(payload.get("email_verified", True)),
        "avatar": payload.get("picture"),
        "name": payload.get("name"),
        "raw": payload,
    }


def _exchange_code(provider: str, config: dict, code: str, verifier: str):
    client_id = os.getenv(config["client_id_env"])
    client_secret = _client_secret(provider, config)
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail=f"{config['label']} OAuth non configure")

    response = requests.post(
        config["token_url"],
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _oauth_redirect_uri(provider),
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": verifier,
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Echange OAuth refuse")
    return response.json()


def _link_or_create_user(conn, provider: str, identity: dict, request: Request):
    ensure_oauth_tables(conn)
    existing_oauth = conn.execute(text("""
        SELECT users.id, users.email, users.profile_completed
        FROM oauth_accounts
        JOIN users ON users.id = oauth_accounts.user_id
        WHERE oauth_accounts.provider = :provider
          AND oauth_accounts.provider_user_id = :provider_user_id
    """), {
        "provider": provider,
        "provider_user_id": identity["provider_user_id"],
    }).fetchone()

    if existing_oauth:
        user_id = existing_oauth.id
        email = existing_oauth.email
        is_new = False
    else:
        user = conn.execute(text("""
            SELECT id, email
            FROM users
            WHERE email = :email
        """), {"email": identity["email"]}).fetchone()

        if user:
            user_id = user.id
            email = user.email
            is_new = False
        else:
            created = conn.execute(text("""
                INSERT INTO users (email, is_verified, verification_attempts, profile_completed)
                VALUES (:email, TRUE, 0, FALSE)
                RETURNING id, email
            """), {"email": identity["email"]}).fetchone()
            user_id = created.id
            email = created.email
            is_new = True
            record_consents(conn, user_id, {
                "terms_accepted": True,
                "privacy_policy_accepted": True,
                "ai_processing_accepted": True,
                "marketing_emails_accepted": False,
                "analytics_accepted": False,
                "personalized_opportunities_accepted": True,
                "weekly_reports_accepted": True,
                "third_party_data_processing_accepted": False,
            }, request)

        conn.execute(text("""
            INSERT INTO oauth_accounts (
                user_id, provider, provider_user_id, provider_email, provider_avatar, updated_at
            )
            VALUES (
                :user_id, :provider, :provider_user_id, :provider_email, :provider_avatar, NOW()
            )
            ON CONFLICT (provider, provider_user_id)
            DO UPDATE SET
                user_id = EXCLUDED.user_id,
                provider_email = EXCLUDED.provider_email,
                provider_avatar = EXCLUDED.provider_avatar,
                updated_at = NOW()
        """), {
            "user_id": user_id,
            "provider": provider,
            "provider_user_id": identity["provider_user_id"],
            "provider_email": identity["email"],
            "provider_avatar": identity.get("avatar"),
        })

    log_security_event(
        conn,
        "oauth_login_success",
        request,
        email=email,
        user_id=user_id,
        metadata={"provider": provider, "new_user": is_new},
    )
    capture_event(conn, "oauth_login", user_id=user_id, email=email, properties={"provider": provider, "new_user": is_new})
    return user_id, email, is_new


@router.get("/providers")
def oauth_providers():
    with engine.begin() as conn:
        ensure_feature_flags_table(conn)
        flags = {
            provider: is_feature_enabled(conn, config.get("flag"), {"plan": "FREE"})
            and _provider_runtime_ready(provider, config)
            for provider, config in PROVIDERS.items()
            if not config.get("coming_soon")
        }

    return {
        "providers": [
            {
                "id": provider,
                "label": config["label"],
                "enabled": bool(flags.get(provider)),
                "coming_soon": bool(config.get("coming_soon", False)),
            }
            for provider, config in PROVIDERS.items()
        ]
    }


@router.get("/{provider}/start")
def oauth_start(provider: str, request: Request, redirect: str | None = "/dashboard"):
    provider, config = _provider_config(provider)
    with engine.begin() as conn:
        ensure_oauth_tables(conn)
        ensure_feature_flags_table(conn)
        ensure_security_tables(conn)
        if not is_feature_enabled(conn, config["flag"], {"plan": "FREE"}):
            raise HTTPException(status_code=403, detail=f"{config['label']} OAuth desactive")

        client_id = os.getenv(config["client_id_env"])
        if not client_id:
            raise HTTPException(status_code=500, detail=f"{config['label']} OAuth non configure")

        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        nonce = secrets.token_urlsafe(32)
        conn.execute(text("""
            INSERT INTO oauth_flows (
                provider, state, code_verifier, nonce, redirect_path,
                ip_address, user_agent, expires_at
            )
            VALUES (
                :provider, :state, :code_verifier, :nonce, :redirect_path,
                :ip_address, :user_agent, NOW() + interval '10 minutes'
            )
        """), {
            "provider": provider,
            "state": state,
            "code_verifier": verifier,
            "nonce": nonce,
            "redirect_path": _redirect_path(redirect),
            "ip_address": _request_ip(request),
            "user_agent": request.headers.get("user-agent"),
        })
        log_security_event(conn, "oauth_flow_started", request, metadata={"provider": provider})

    query = {
        "client_id": client_id,
        "redirect_uri": _oauth_redirect_uri(provider),
        "response_type": "code",
        "scope": " ".join(config["scopes"]),
        "state": state,
        "nonce": nonce,
        "code_challenge": _code_challenge(verifier),
        "code_challenge_method": "S256",
    }
    return RedirectResponse(f"{config['auth_url']}?{urlencode(query)}", status_code=302)


@router.get("/{provider}/callback")
@router.post("/{provider}/callback")
async def oauth_callback(provider: str, request: Request):
    provider, config = _provider_config(provider)
    if request.method == "POST":
        form = await request.form()
        code = form.get("code")
        state = form.get("state")
    else:
        code = request.query_params.get("code")
        state = request.query_params.get("state")

    if not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/login?oauth_error=missing_code", status_code=302)

    try:
        with engine.begin() as conn:
            ensure_oauth_tables(conn)
            flow = conn.execute(text("""
                SELECT state, code_verifier, nonce, redirect_path
                FROM oauth_flows
                WHERE provider = :provider
                  AND state = :state
                  AND consumed_at IS NULL
                  AND expires_at > NOW()
            """), {"provider": provider, "state": state}).fetchone()

            if not flow:
                log_security_event(conn, "oauth_invalid_state", request, severity="warning", metadata={"provider": provider})
                raise HTTPException(status_code=400, detail="State OAuth invalide")

            conn.execute(text("UPDATE oauth_flows SET consumed_at = NOW() WHERE state = :state"), {"state": state})

        token_data = _exchange_code(provider, config, str(code), flow.code_verifier)
        identity = _verify_id_token(token_data.get("id_token"), provider, config, flow.nonce)

        with engine.begin() as conn:
            user_id, email, is_new = _link_or_create_user(conn, provider, identity, request)
            session_token = secrets.token_urlsafe(32)
            conn.execute(text("""
                INSERT INTO oauth_login_sessions (user_id, token, expires_at)
                VALUES (:user_id, :token, NOW() + interval '5 minutes')
            """), {"user_id": user_id, "token": session_token})

        redirect_path = "/onboarding" if is_new else flow.redirect_path
        return RedirectResponse(
            f"{FRONTEND_URL}/auth/callback?session={session_token}&redirect={redirect_path}",
            status_code=302,
        )
    except Exception:
        with engine.begin() as conn:
            log_security_event(conn, "oauth_callback_failed", request, severity="warning", metadata={"provider": provider})
        return RedirectResponse(f"{FRONTEND_URL}/login?oauth_error=failed", status_code=302)


@router.post("/session/{session_token}")
def oauth_session_exchange(session_token: str, request: Request):
    with engine.begin() as conn:
        ensure_oauth_tables(conn)
        row = conn.execute(text("""
            SELECT oauth_login_sessions.user_id, users.email, users.profile_completed
            FROM oauth_login_sessions
            JOIN users ON users.id = oauth_login_sessions.user_id
            WHERE oauth_login_sessions.token = :token
              AND oauth_login_sessions.consumed_at IS NULL
              AND oauth_login_sessions.expires_at > NOW()
        """), {"token": session_token}).fetchone()

        if not row:
            log_security_event(conn, "oauth_session_invalid", request, severity="warning")
            raise HTTPException(status_code=400, detail="Session OAuth invalide")

        conn.execute(text("""
            UPDATE oauth_login_sessions
            SET consumed_at = NOW()
            WHERE token = :token
        """), {"token": session_token})
        log_security_event(conn, "oauth_session_exchanged", request, email=row.email, user_id=row.user_id)

    return {
        "access_token": create_token({"sub": row.email}),
        "state": "READY" if row.profile_completed else "ONBOARDING_REQUIRED",
    }


@router.get("/admin/stats")
def oauth_admin_stats(request: Request, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_oauth_tables(conn)
        require_security_admin(conn, email, request)
        providers = conn.execute(text("""
            SELECT provider, COUNT(*) AS accounts
            FROM oauth_accounts
            GROUP BY provider
            ORDER BY accounts DESC
        """)).fetchall()
        failures = conn.execute(text("""
            SELECT event_type, COUNT(*) AS events
            FROM security_audit_logs
            WHERE event_type LIKE 'oauth_%'
              AND severity IN ('warning', 'critical')
              AND created_at >= NOW() - interval '7 days'
            GROUP BY event_type
            ORDER BY events DESC
        """)).fetchall()

    return {
        "providers": [{"provider": row.provider, "accounts": int(row.accounts or 0)} for row in providers],
        "failures_7d": [{"event_type": row.event_type, "events": int(row.events or 0)} for row in failures],
    }
