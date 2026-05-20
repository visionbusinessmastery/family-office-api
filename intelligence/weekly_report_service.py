import logging
import os
import json
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from intelligence.category_opportunities import get_category_opportunities
from product.entitlements import resolve_effective_plan


router = APIRouter()
logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", os.getenv("FRONTEND_URL_PROD", "https://vision-business.com"))


def ensure_weekly_report_tables(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS weekly_reports (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'FREE',
            subject TEXT NOT NULL,
            payload JSONB,
            status TEXT NOT NULL DEFAULT 'pending',
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_weekly_reports_user_created
        ON weekly_reports(user_id, created_at DESC)
    """))


def _safe_count(conn, query: str, params: dict) -> int:
    try:
        return int(conn.execute(text(query), params).scalar() or 0)
    except Exception:
        return 0


def _safe_sum(conn, query: str, params: dict) -> float:
    try:
        return float(conn.execute(text(query), params).scalar() or 0)
    except Exception:
        return 0.0


def build_weekly_report_payload(conn, user_id: int, email: str) -> dict:
    row = conn.execute(text("""
        SELECT
            users.plan AS user_plan,
            users.level,
            subscriptions.plan AS subscription_plan,
            subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.id = :user_id
    """), {"user_id": user_id}).fetchone()

    plan = resolve_effective_plan(
        row.user_plan if row else "FREE",
        row.subscription_plan if row else None,
        row.subscription_status if row else None,
    )

    portfolio_value = _safe_sum(
        conn,
        "SELECT COALESCE(SUM(quantity * purchase_price), 0) FROM portfolio WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    real_estate_count = _safe_count(
        conn,
        "SELECT COUNT(*) FROM real_estate_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    venture_count = _safe_count(
        conn,
        "SELECT COUNT(*) FROM venture_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )

    xp_row = conn.execute(text("""
        SELECT xp, streak
        FROM progression_profiles
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    opportunities = []
    try:
        # Reuse existing route function shape while avoiding new provider calls here.
        opportunities = get_category_opportunities(email).get("categories", [])[:4]
    except Exception:
        opportunities = []

    risk_alerts = []
    if portfolio_value == 0:
        risk_alerts.append("Ton portefeuille financier reste a construire.")
    if real_estate_count == 0:
        risk_alerts.append("Aucune poche immobiliere renseignee pour l'instant.")
    if venture_count == 0 and plan in ["ELITE", "LIBERTY", "LEGACY"]:
        risk_alerts.append("Ton espace business peut encore enrichir la consolidation patrimoniale.")

    return {
        "email": email,
        "plan": plan,
        "level": row.level if row else None,
        "portfolio_value": round(portfolio_value, 2),
        "xp": int(xp_row.xp or 0) if xp_row else 0,
        "streak": int(xp_row.streak or 0) if xp_row else 0,
        "opportunities": opportunities,
        "risk_alerts": risk_alerts[:3],
        "challenge": "Choisir une action patrimoniale simple et la finaliser avant dimanche.",
        "ethan_tip": "La progression vient d'une petite decision bien executee, repetee chaque semaine.",
        "generated_at": datetime.utcnow().isoformat(),
    }


def _render_report_html(payload: dict) -> str:
    opportunities = "".join(
        f"<li><strong>{item.get('title', 'Opportunite')}</strong> - {item.get('quick_action', 'Action a verifier')}</li>"
        for item in payload.get("opportunities", [])
    ) or "<li>Aucune opportunite urgente cette semaine. Continue a enrichir tes donnees.</li>"

    alerts = "".join(
        f"<li>{alert}</li>"
        for alert in payload.get("risk_alerts", [])
    ) or "<li>Aucune alerte prioritaire.</li>"

    return f"""
    <div style="font-family:Arial,sans-serif;background:#05070b;color:#f5f5f5;padding:28px;">
      <div style="max-width:640px;margin:auto;background:#090d14;border:1px solid #1f2937;border-radius:18px;padding:24px;">
        <p style="letter-spacing:3px;color:#3fa9f5;font-size:11px;">WHITE ROCK</p>
        <h1 style="margin:8px 0 0;">Ton rapport patrimonial hebdomadaire</h1>
        <p style="color:#a1a1aa;">Ethan a resume ta progression, tes signaux et ton action prioritaire.</p>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:22px 0;">
          <div><small>Plan</small><br><strong>{payload.get('plan')}</strong></div>
          <div><small>XP</small><br><strong>{payload.get('xp')}</strong></div>
          <div><small>Portefeuille</small><br><strong>{payload.get('portfolio_value')} EUR</strong></div>
        </div>
        <h3>Opportunites</h3>
        <ul>{opportunities}</ul>
        <h3>Alertes calmes</h3>
        <ul>{alerts}</ul>
        <h3>Challenge</h3>
        <p>{payload.get('challenge')}</p>
        <blockquote style="border-left:3px solid #f4c95d;padding-left:14px;color:#e5e7eb;">
          {payload.get('ethan_tip')}
        </blockquote>
        <p><a href="{FRONTEND_URL}/dashboard" style="color:#3fa9f5;">Ouvrir mon cockpit</a></p>
      </div>
    </div>
    """


def send_weekly_report(email: str, payload: dict) -> bool:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY missing, weekly report skipped for %s", email)
        return False

    response = requests.post(
        "https://api.resend.com/emails",
        json={
            "from": "WHITE ROCK <reports@vision-business.com>",
            "to": [email],
            "subject": "Ton rapport WHITE ROCK de la semaine",
            "html": _render_report_html(payload),
        },
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=12,
    )
    return response.status_code in [200, 201, 202]


@router.get("/weekly-report/preview")
def preview_weekly_report(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_weekly_report_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        return build_weekly_report_payload(conn, user_id, email)


@router.post("/weekly-report/send")
def send_current_user_weekly_report(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_weekly_report_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        payload = build_weekly_report_payload(conn, user_id, email)

        recent = conn.execute(text("""
            SELECT id
            FROM weekly_reports
            WHERE user_id = :user_id
              AND created_at > :since
              AND status = 'sent'
            LIMIT 1
        """), {"user_id": user_id, "since": datetime.utcnow() - timedelta(days=6)}).fetchone()

        if recent:
            return {"status": "already_sent_recently", "payload": payload}

        sent = send_weekly_report(email, payload)
        conn.execute(text("""
            INSERT INTO weekly_reports (user_id, email, plan, subject, payload, status, sent_at)
            VALUES (:user_id, :email, :plan, :subject, CAST(:payload AS JSONB), :status, :sent_at)
        """), {
            "user_id": user_id,
            "email": email,
            "plan": payload["plan"],
            "subject": "Ton rapport WHITE ROCK de la semaine",
            "payload": json.dumps(payload),
            "status": "sent" if sent else "skipped",
            "sent_at": datetime.utcnow() if sent else None,
        })

    return {"status": "sent" if sent else "skipped", "payload": payload}
