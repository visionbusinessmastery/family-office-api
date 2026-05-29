import logging
import os
import json
from datetime import datetime, timedelta

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from intelligence.category_opportunities import get_category_opportunities
from product.entitlements import plan_allows, resolve_effective_plan


router = APIRouter()
logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", os.getenv("FRONTEND_URL_PROD", "https://vision-business.com"))
WEEKLY_REPORT_CRON_SECRET = os.getenv("WEEKLY_REPORT_CRON_SECRET")
WEEKLY_REPORT_CRON_BATCH_SIZE = int(os.getenv("WEEKLY_REPORT_CRON_BATCH_SIZE", "25"))


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

    profile = conn.execute(text("""
        SELECT goals, investor_profile, motivation, has_children,
               transmission_goal, governance_need
        FROM user_wealth_profiles
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()
    goals = [item for item in (profile.goals or "").split("|") if item] if profile else []
    has_children = bool(profile.has_children) if profile else False
    motivation = profile.motivation if profile else None
    professional_context = profile.investor_profile if profile else None

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

    data_alerts = []
    if portfolio_value == 0:
        data_alerts.append("Portefeuille financier non renseigne.")
    if real_estate_count == 0:
        data_alerts.append("Poche immobiliere non renseignee.")
    if venture_count == 0 and plan in ["ELITE", "LIBERTY", "LEGACY"]:
        data_alerts.append("Espace business disponible mais non renseigne.")

    if has_children and plan in ["LIBERTY", "LEGACY"]:
        data_alerts.append("Contexte familial disponible pour consolidation.")

    if "marketing" in str(professional_context or "").lower() or "revenu" in " ".join(goals).lower():
        main_opportunity = {
            "title": "Offre premium basee sur ton expertise",
            "why": "Signal issu du contexte professionnel renseigne.",
            "next_action": "Disponible dans le cockpit.",
        }
    elif opportunities:
        first = opportunities[0]
        main_opportunity = {
            "title": first.get("title", "Signal prioritaire"),
            "why": first.get("analysis") or first.get("quick_action") or "Signal coherent avec le cockpit actuel.",
            "next_action": "Disponible dans le cockpit.",
        }
    else:
        main_opportunity = {
            "title": "Contexte a enrichir",
            "why": "Signal neutre: donnees encore partielles.",
            "next_action": "Disponible dans le cockpit.",
        }

    mission = (
        "Mission disponible: contexte familial a completer."
        if has_children and plan in ["LIBERTY", "LEGACY"]
        else "Mission disponible: contexte revenu ou patrimoine a completer."
    )

    return {
        "email": email,
        "plan": plan,
        "level": plan,
        "profile": {
            "goals": goals,
            "motivation": motivation,
            "professional_context": professional_context,
            "has_children": has_children,
        },
        "portfolio_value": round(portfolio_value, 2),
        "xp": int(xp_row.xp or 0) if xp_row else 0,
        "streak": int(xp_row.streak or 0) if xp_row else 0,
        "opportunities": opportunities,
        "main_opportunity": main_opportunity,
        "data_alerts": data_alerts[:3],
        "risk_alerts": data_alerts[:3],
        "challenge": mission,
        "context_note": "Synthese de distribution basee sur les donnees renseignees cette semaine.",
        "generated_at": datetime.utcnow().isoformat(),
    }


def _render_report_html(payload: dict) -> str:
    opportunities = "".join(
        f"<li><strong>{item.get('title', 'Signal')}</strong> - {item.get('quick_action', 'Donnee a verifier')}</li>"
        for item in payload.get("opportunities", [])
    ) or "<li>Aucune opportunite urgente cette semaine. Continue a enrichir tes donnees.</li>"

    alerts = "".join(
        f"<li>{alert}</li>"
        for alert in payload.get("data_alerts", payload.get("risk_alerts", []))
    ) or "<li>Aucun signal prioritaire.</li>"
    main_opportunity = payload.get("main_opportunity") or {}

    return f"""
    <div style="font-family:Arial,sans-serif;background:#05070b;color:#f5f5f5;padding:28px;">
      <div style="max-width:640px;margin:auto;background:#090d14;border:1px solid #1f2937;border-radius:18px;padding:24px;">
        <p style="letter-spacing:3px;color:#3fa9f5;font-size:11px;">WHITE ROCK</p>
        <h1 style="margin:8px 0 0;">Ton rapport patrimonial hebdomadaire</h1>
        <p style="color:#a1a1aa;">Synthese de ta progression, de tes signaux et de ton contexte de la semaine.</p>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:22px 0;">
          <div><small>Plan</small><br><strong>{payload.get('plan')}</strong></div>
          <div><small>XP</small><br><strong>{payload.get('xp')}</strong></div>
          <div><small>Portefeuille</small><br><strong>{payload.get('portfolio_value')} EUR</strong></div>
        </div>
        <h3>Signal principal</h3>
        <p><strong>{main_opportunity.get('title', 'Signal prioritaire')}</strong></p>
        <p style="color:#cbd5e1;">{main_opportunity.get('why', '')}</p>
        <p style="color:#93c5fd;">{main_opportunity.get('next_action', '')}</p>
        <h3>Autres signaux</h3>
        <ul>{opportunities}</ul>
        <h3>Signaux de vigilance</h3>
        <ul>{alerts}</ul>
        <h3>Challenge</h3>
        <p>{payload.get('challenge')}</p>
        <blockquote style="border-left:3px solid #f4c95d;padding-left:14px;color:#e5e7eb;">
          {payload.get('context_note', '')}
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
        payload = build_weekly_report_payload(conn, user_id, email)
        if not plan_allows(payload["plan"], "GOLD"):
            raise HTTPException(status_code=403, detail="Weekly insights require GOLD or higher")
        return payload


@router.post("/weekly-report/send")
def send_current_user_weekly_report(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_weekly_report_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        payload = build_weekly_report_payload(conn, user_id, email)
        if not plan_allows(payload["plan"], "GOLD"):
            raise HTTPException(status_code=403, detail="Weekly insights require GOLD or higher")

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


@router.post("/weekly-report/send-due")
def send_due_weekly_reports(request: Request):
    if not WEEKLY_REPORT_CRON_SECRET:
        raise HTTPException(status_code=503, detail="Weekly report cron secret not configured")

    if request.headers.get("x-cron-secret") != WEEKLY_REPORT_CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid cron secret")

    batch_size = max(1, min(WEEKLY_REPORT_CRON_BATCH_SIZE, 100))
    since = datetime.utcnow() - timedelta(days=6)
    summary = {"sent": 0, "skipped": 0, "failed": 0, "already_sent_recently": 0, "not_eligible": 0}

    with engine.begin() as conn:
        ensure_weekly_report_tables(conn)
        users = conn.execute(text("""
            SELECT id, email
            FROM users
            WHERE email IS NOT NULL
            ORDER BY id ASC
            LIMIT :limit
        """), {"limit": batch_size}).fetchall()

        for user in users:
            recent = conn.execute(text("""
                SELECT id
                FROM weekly_reports
                WHERE user_id = :user_id
                  AND created_at > :since
                  AND status = 'sent'
                LIMIT 1
            """), {"user_id": user.id, "since": since}).fetchone()

            if recent:
                summary["already_sent_recently"] += 1
                continue

            payload = build_weekly_report_payload(conn, user.id, user.email)
            if not plan_allows(payload["plan"], "GOLD"):
                summary["not_eligible"] += 1
                continue

            status = "skipped"
            sent_at = None

            try:
                sent = send_weekly_report(user.email, payload)
                if sent:
                    status = "sent"
                    sent_at = datetime.utcnow()
                    summary["sent"] += 1
                else:
                    summary["skipped"] += 1
            except Exception:
                logger.exception("Weekly report failed for user_id=%s", user.id)
                status = "failed"
                summary["failed"] += 1

            conn.execute(text("""
                INSERT INTO weekly_reports (user_id, email, plan, subject, payload, status, sent_at)
                VALUES (:user_id, :email, :plan, :subject, CAST(:payload AS JSONB), :status, :sent_at)
            """), {
                "user_id": user.id,
                "email": user.email,
                "plan": payload["plan"],
                "subject": "Ton rapport WHITE ROCK de la semaine",
                "payload": json.dumps(payload),
                "status": status,
                "sent_at": sent_at,
            })

    return {"status": "ok", "batch_size": batch_size, "summary": summary}
