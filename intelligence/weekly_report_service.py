import logging
import os
import json
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

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
REPORT_TIMEZONE = os.getenv("REPORT_TIMEZONE", "Europe/Paris")
REPORT_SCHEDULER_ENABLED = os.getenv("WEEKLY_REPORT_SCHEDULER_ENABLED", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
REPORT_FROM_EMAIL = os.getenv("REPORT_FROM_EMAIL", "WHITE ROCK <reports@vision-business.com>")
REPORT_DEFINITIONS = {
    0: {
        "type": "monday",
        "label": "Rapport du lundi",
        "subject": "WHITE ROCK - Ton cadrage patrimonial du lundi",
        "challenge": "Choisir une action patrimoniale simple et la finaliser avant vendredi.",
        "ethan_tip": "Le lundi sert a choisir la bonne direction: une priorite, une action, un resultat attendu.",
    },
    4: {
        "type": "friday",
        "label": "Rapport du vendredi",
        "subject": "WHITE ROCK - Ton bilan patrimonial du vendredi",
        "challenge": "Identifier ce qui a progresse cette semaine et preparer la prochaine decision utile.",
        "ethan_tip": "Le vendredi sert a transformer la semaine en apprentissage: ce qui a avance, ce qui bloque, ce qui merite le prochain effort.",
    },
}


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

    conn.execute(text("""
        ALTER TABLE weekly_reports
        ADD COLUMN IF NOT EXISTS report_type TEXT NOT NULL DEFAULT 'weekly'
    """))

    conn.execute(text("""
        ALTER TABLE weekly_reports
        ADD COLUMN IF NOT EXISTS period_key TEXT
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_reports_unique_sent
        ON weekly_reports(user_id, report_type, period_key)
        WHERE status = 'sent' AND period_key IS NOT NULL
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


def build_weekly_report_payload(conn, user_id: int, email: str, report_type: str = "weekly") -> dict:
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
    finance_rows = conn.execute(text("""
        SELECT type, COALESCE(SUM(amount), 0) AS total
        FROM finance_items
        WHERE user_id = :user_id
        GROUP BY type
    """), {"user_id": user_id}).fetchall()
    finance_totals = {row.type: float(row.total or 0) for row in finance_rows}
    monthly_income = finance_totals.get("revenus", 0)
    monthly_expenses = finance_totals.get("charges", 0)
    monthly_cashflow = monthly_income - monthly_expenses
    savings_total = finance_totals.get("epargne", 0)
    debt_total = finance_totals.get("dettes", 0)

    real_estate_count = _safe_count(
        conn,
        "SELECT COUNT(*) FROM real_estate_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    real_estate_value = _safe_sum(
        conn,
        """
        SELECT COALESCE(SUM(GREATEST(estimated_value, resale_price, purchase_price)), 0)
        FROM real_estate_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    venture_count = _safe_count(
        conn,
        "SELECT COUNT(*) FROM venture_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    business_value = _safe_sum(
        conn,
        """
        SELECT COALESCE(SUM(
            CASE
                WHEN valuation > 0 THEN valuation
                ELSE GREATEST((revenue - charges) + fundraising - debts, 0)
            END
        ), 0)
        FROM venture_assets
        WHERE user_id = :user_id
        """,
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
        "report_type": report_type,
        "report_label": "Rapport du vendredi" if report_type == "friday" else "Rapport du lundi" if report_type == "monday" else "Rapport hebdomadaire",
        "plan": plan,
        "level": plan,
        "portfolio_value": round(portfolio_value, 2),
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses": round(monthly_expenses, 2),
        "monthly_cashflow": round(monthly_cashflow, 2),
        "savings_total": round(savings_total, 2),
        "debt_total": round(debt_total, 2),
        "real_estate_count": real_estate_count,
        "real_estate_value": round(real_estate_value, 2),
        "venture_count": venture_count,
        "business_value": round(business_value, 2),
        "visible_wealth": round(portfolio_value + savings_total + real_estate_value + business_value, 2),
        "xp": int(xp_row.xp or 0) if xp_row else 0,
        "streak": int(xp_row.streak or 0) if xp_row else 0,
        "opportunities": opportunities,
        "risk_alerts": risk_alerts[:3],
        "challenge": REPORT_DEFINITIONS.get(4 if report_type == "friday" else 0, {}).get(
            "challenge",
            "Choisir une action patrimoniale simple et la finaliser avant dimanche.",
        ),
        "ethan_tip": REPORT_DEFINITIONS.get(4 if report_type == "friday" else 0, {}).get(
            "ethan_tip",
            "La progression vient d'une petite decision bien executee, repetee chaque semaine.",
        ),
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
        <h1 style="margin:8px 0 0;">{payload.get('report_label', 'Ton rapport patrimonial')}</h1>
        <p style="color:#a1a1aa;">Ethan a resume ta progression, tes signaux et ton action prioritaire.</p>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:22px 0;">
          <div><small>Plan</small><br><strong>{payload.get('plan')}</strong></div>
          <div><small>XP</small><br><strong>{payload.get('xp')}</strong></div>
          <div><small>Patrimoine visible</small><br><strong>{payload.get('visible_wealth')} EUR</strong></div>
        </div>
        <h3>Situation mensuelle</h3>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:12px 0;">
          <div><small>Revenus</small><br><strong>{payload.get('monthly_income')} EUR</strong></div>
          <div><small>Charges</small><br><strong>{payload.get('monthly_expenses')} EUR</strong></div>
          <div><small>Cashflow</small><br><strong>{payload.get('monthly_cashflow')} EUR</strong></div>
        </div>
        <h3>Bilan patrimonial</h3>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0;">
          <div><small>Epargne</small><br><strong>{payload.get('savings_total')} EUR</strong></div>
          <div><small>Dettes</small><br><strong>{payload.get('debt_total')} EUR</strong></div>
          <div><small>Immobilier</small><br><strong>{payload.get('real_estate_value')} EUR</strong></div>
          <div><small>Business</small><br><strong>{payload.get('business_value')} EUR</strong></div>
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


def subject_for_report(report_type: str) -> str:
    if report_type == "friday":
        return REPORT_DEFINITIONS[4]["subject"]
    if report_type == "monday":
        return REPORT_DEFINITIONS[0]["subject"]
    return "Ton rapport WHITE ROCK de la semaine"


def send_weekly_report(email: str, payload: dict) -> bool:
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY missing, weekly report skipped for %s", email)
        return False

    response = requests.post(
        "https://api.resend.com/emails",
        json={
            "from": REPORT_FROM_EMAIL,
            "to": [email],
            "subject": subject_for_report(payload.get("report_type", "weekly")),
            "html": _render_report_html(payload),
        },
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        timeout=12,
    )
    return response.status_code in [200, 201, 202]


def current_report_window(now: datetime | None = None):
    current = now or datetime.now(ZoneInfo(REPORT_TIMEZONE))
    return REPORT_DEFINITIONS.get(current.weekday()), current


def period_key_for(now: datetime, report_type: str) -> str:
    iso_year, iso_week, _ = now.isocalendar()
    return f"{iso_year}-W{iso_week:02d}-{report_type}"


def user_accepts_weekly_reports(row) -> bool:
    preference = getattr(row, "weekly_reports", None)
    return preference is None or str(preference).lower() == "true"


def send_due_weekly_reports(now: datetime | None = None, force_report_type: str | None = None) -> dict:
    report_def, current = current_report_window(now)

    if force_report_type:
        report_type = force_report_type
        if report_type not in {"monday", "friday"}:
            raise HTTPException(status_code=400, detail="report_type invalide")
        report_def = REPORT_DEFINITIONS[4 if report_type == "friday" else 0]
    elif not report_def:
        return {"status": "not_due_today", "sent": 0, "skipped": 0, "failed": 0}

    report_type = report_def["type"]
    period_key = period_key_for(current, report_type)
    sent_count = 0
    skipped_count = 0
    failed_count = 0

    with engine.begin() as conn:
        ensure_weekly_report_tables(conn)
        conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"weekly_reports:{report_type}:{period_key}"},
        )
        users = conn.execute(text("""
            SELECT
                users.id,
                users.email,
                privacy_preferences.email_preferences->>'weekly_reports' AS weekly_reports
            FROM users
            LEFT JOIN privacy_preferences ON privacy_preferences.user_id = users.id
            WHERE users.email IS NOT NULL
              AND COALESCE(users.is_verified, TRUE) = TRUE
        """)).fetchall()

        for user in users:
            if not user_accepts_weekly_reports(user):
                skipped_count += 1
                continue

            existing = conn.execute(text("""
                SELECT id
                FROM weekly_reports
                WHERE user_id = :user_id
                  AND report_type = :report_type
                  AND period_key = :period_key
                  AND status = 'sent'
                LIMIT 1
            """), {
                "user_id": user.id,
                "report_type": report_type,
                "period_key": period_key,
            }).fetchone()

            if existing:
                skipped_count += 1
                continue

            payload = build_weekly_report_payload(conn, user.id, user.email, report_type)
            sent = send_weekly_report(user.email, payload)
            status = "sent" if sent else "skipped"

            conn.execute(text("""
                INSERT INTO weekly_reports (
                    user_id, email, plan, subject, payload, status, sent_at, report_type, period_key
                )
                VALUES (
                    :user_id, :email, :plan, :subject, CAST(:payload AS JSONB),
                    :status, :sent_at, :report_type, :period_key
                )
            """), {
                "user_id": user.id,
                "email": user.email,
                "plan": payload["plan"],
                "subject": subject_for_report(report_type),
                "payload": json.dumps(payload),
                "status": status,
                "sent_at": datetime.utcnow() if sent else None,
                "report_type": report_type,
                "period_key": period_key,
            })

            if sent:
                sent_count += 1
            else:
                failed_count += 1

    return {
        "status": "completed",
        "report_type": report_type,
        "period_key": period_key,
        "sent": sent_count,
        "skipped": skipped_count,
        "failed": failed_count,
    }


async def weekly_report_scheduler_loop():
    if not REPORT_SCHEDULER_ENABLED:
        logger.info("Weekly report scheduler disabled")
        return

    logger.info("Weekly report scheduler started timezone=%s", REPORT_TIMEZONE)
    while True:
        try:
            result = send_due_weekly_reports()
            if result.get("status") == "completed":
                logger.info("Weekly report run result=%s", result)
        except Exception as exc:
            logger.exception("Weekly report scheduler failed: %s", exc)

        await asyncio.sleep(60 * 60)


@router.get("/weekly-report/preview")
def preview_weekly_report(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_weekly_report_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        report_def, _ = current_report_window()
        report_type = report_def["type"] if report_def else "monday"
        return build_weekly_report_payload(conn, user_id, email, report_type)


@router.post("/weekly-report/send")
def send_current_user_weekly_report(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_weekly_report_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")
        report_def, current = current_report_window()
        report_type = report_def["type"] if report_def else "monday"
        period_key = period_key_for(current, report_type)
        payload = build_weekly_report_payload(conn, user_id, email, report_type)

        recent = conn.execute(text("""
            SELECT id
            FROM weekly_reports
            WHERE user_id = :user_id
              AND report_type = :report_type
              AND period_key = :period_key
              AND status = 'sent'
            LIMIT 1
        """), {
            "user_id": user_id,
            "report_type": report_type,
            "period_key": period_key,
        }).fetchone()

        if recent:
            return {"status": "already_sent_recently", "payload": payload}

        sent = send_weekly_report(email, payload)
        conn.execute(text("""
            INSERT INTO weekly_reports (
                user_id, email, plan, subject, payload, status, sent_at, report_type, period_key
            )
            VALUES (
                :user_id, :email, :plan, :subject, CAST(:payload AS JSONB),
                :status, :sent_at, :report_type, :period_key
            )
        """), {
            "user_id": user_id,
            "email": email,
            "plan": payload["plan"],
            "subject": subject_for_report(report_type),
            "payload": json.dumps(payload),
            "status": "sent" if sent else "skipped",
            "sent_at": datetime.utcnow() if sent else None,
            "report_type": report_type,
            "period_key": period_key,
        })

    return {"status": "sent" if sent else "skipped", "payload": payload}


@router.post("/weekly-report/run-due")
def run_due_weekly_reports(report_type: str | None = None, email: str = Depends(get_current_user)):
    if not email.endswith("@vision-business.com"):
        raise HTTPException(status_code=403, detail="Admin requis")

    return send_due_weekly_reports(force_report_type=report_type)
