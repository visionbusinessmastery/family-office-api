import os
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from auth.utils import get_current_user
from core.cache import delete_cache_keys, delete_cache_patterns
from database import engine
from product.entitlements import normalize_plan, resolve_effective_plan
from security.audit import ensure_security_tables, log_security_event
from analytics.analytics_events import SUBSCRIPTION_UPGRADED, FOUNDER_UPGRADE
from analytics.posthog_service import capture_event
from monitoring.sentry_config import capture_exception


router = APIRouter()
_billing_schema_ready = False
logger = logging.getLogger(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://vision-business.com")

PLANS = {
    "free": {
        "name": "Free - Foundation",
        "price_env": None,
        "description": "Fondations financieres, progression et guidance simple.",
    },
    "gold": {
        "name": "Gold - Growth",
        "price_env": "STRIPE_PRICE_GOLD",
        "description": "Croissance patrimoniale, analytics, immobilier, opportunites et guidance avancee.",
    },
    "elite": {
        "name": "Elite - Wealth OS",
        "price_env": "STRIPE_PRICE_ELITE",
        "description": "Family Office OS, multi-user, gouvernance, guidance premium et consolidation.",
    },
    "liberty": {
        "name": "Liberty - Financial Freedom",
        "price_env": "STRIPE_PRICE_LIBERTY",
        "description": "Liberte financiere, ecosysteme Wealth OS complet, guidance premium et pilotage avance.",
    },
    "legacy": {
        "name": "Legacy - Dynasty Office",
        "price_env": "STRIPE_PRICE_LEGACY",
        "description": "Transmission, gouvernance familiale, protection patrimoniale et strategie multi-generationnelle.",
    },
}

PLAN_INTERVALS = ("monthly", "yearly")

PLAN_PRICE_ENVS = {
    "gold": {
        "monthly": "STRIPE_PRICE_GOLD_MONTHLY",
        "yearly": "STRIPE_PRICE_GOLD_YEARLY",
        "legacy": "STRIPE_PRICE_GOLD",
    },
    "elite": {
        "monthly": "STRIPE_PRICE_ELITE_MONTHLY",
        "yearly": "STRIPE_PRICE_ELITE_YEARLY",
        "legacy": "STRIPE_PRICE_ELITE",
    },
    "liberty": {
        "monthly": "STRIPE_PRICE_LIBERTY_MONTHLY",
        "yearly": "STRIPE_PRICE_LIBERTY_YEARLY",
        "legacy": "STRIPE_PRICE_LIBERTY",
    },
    "legacy": {
        "monthly": "STRIPE_PRICE_LEGACY_MONTHLY",
        "yearly": "STRIPE_PRICE_LEGACY_YEARLY",
        "legacy": "STRIPE_PRICE_LEGACY",
    },
}

FOUNDER_PRICE_ENVS = {
    "gold": {
        "monthly": "STRIPE_PRICE_FOUNDER_GOLD_MONTHLY",
        "yearly": "STRIPE_PRICE_FOUNDER_GOLD_YEARLY",
    },
    "elite": {
        "monthly": "STRIPE_PRICE_FOUNDER_ELITE_MONTHLY",
        "yearly": "STRIPE_PRICE_FOUNDER_ELITE_YEARLY",
    },
    "liberty": {
        "monthly": "STRIPE_PRICE_FOUNDER_LIBERTY_MONTHLY",
        "yearly": "STRIPE_PRICE_FOUNDER_LIBERTY_YEARLY",
    },
    "legacy": {
        "monthly": "STRIPE_PRICE_FOUNDER_LEGACY_MONTHLY",
        "yearly": "STRIPE_PRICE_FOUNDER_LEGACY_YEARLY",
    },
}

STRIPE_STATUS_MAP = {
    "trialing": "trialing",
    "active": "active",
    "past_due": "past_due",
    "canceled": "canceled",
    "cancelled": "canceled",
    "unpaid": "past_due",
    "incomplete": "pending",
    "incomplete_expired": "expired",
    "paused": "paused",
}


def normalize_subscription_status(status: str | None) -> str:
    return STRIPE_STATUS_MAP.get(str(status or "").lower(), "inactive")


def invalidate_subscription_caches(email: str | None, user_id: int | None = None):
    if email:
        delete_cache_keys(f"score:{email}")
        delete_cache_patterns(
            f"intel:{email}*",
            f"context:{email}*",
            f"gamification:{email}*",
            f"quests:{email}*",
        )

    if user_id:
        delete_cache_keys(
            f"cmd_center:{user_id}",
            f"financial:{user_id}",
            f"badges:{user_id}",
        )


def plan_from_price_id(price_id: str | None):
    if not price_id:
        return None

    for plan_id, envs in PLAN_PRICE_ENVS.items():
        for env_name in envs.values():
            configured = os.getenv(env_name or "")
            if configured and configured == price_id:
                return plan_id.upper()

    for plan_id, envs in FOUNDER_PRICE_ENVS.items():
        for env_name in envs.values():
            configured = os.getenv(env_name or "")
            if configured and configured == price_id:
                return plan_id.upper()

    return None


def ensure_billing_tables(conn):
    global _billing_schema_ready

    if _billing_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            plan TEXT NOT NULL DEFAULT 'FREE',
            status TEXT NOT NULL DEFAULT 'inactive',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            current_period_end TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_price_id TEXT"))
    conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS environment TEXT DEFAULT 'sandbox'"))
    conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_founder BOOLEAN DEFAULT FALSE"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS founder_tier TEXT"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS founder_discount INTEGER DEFAULT 0"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS level TEXT DEFAULT 'BEGINNER'"))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS billing_invoices (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            stripe_invoice_id TEXT UNIQUE,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            amount_due INTEGER DEFAULT 0,
            amount_paid INTEGER DEFAULT 0,
            currency TEXT DEFAULT 'eur',
            status TEXT,
            hosted_invoice_url TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS subscription_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            stripe_event_id TEXT UNIQUE,
            event_type TEXT NOT NULL,
            plan TEXT,
            status TEXT,
            payload TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    _billing_schema_ready = True


def normalize_interval(value: str | None):
    interval = str(value or "monthly").lower()
    return interval if interval in PLAN_INTERVALS else "monthly"


def get_price_env(plan_id: str, interval: str, founder: bool = False):
    envs = FOUNDER_PRICE_ENVS if founder else PLAN_PRICE_ENVS
    plan_envs = envs.get(plan_id) or {}
    return plan_envs.get(interval)


def get_plan_or_400(plan_id: str, interval: str | None = None, founder: bool = False):
    plan_id = (plan_id or "").lower()
    plan = PLANS.get(plan_id)

    if not plan or plan_id == "free":
        raise HTTPException(status_code=400, detail="Plan inconnu")

    billing_interval = normalize_interval(interval)
    price_env = get_price_env(plan_id, billing_interval, founder)
    price_id = os.getenv(price_env or "")

    if not price_id and not founder:
        price_env = PLAN_PRICE_ENVS.get(plan_id, {}).get("legacy")
        price_id = os.getenv(price_env or "")

    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"Price Stripe manquant: {price_env}",
        )

    return plan, price_id, price_env, billing_interval


def get_user_subscription(conn, email: str):
    user = conn.execute(text("""
        SELECT id, plan, is_founder, founder_tier, founder_discount
        FROM users
        WHERE email = :email
    """), {"email": email}).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    subscription = conn.execute(text("""
        SELECT plan, status, current_period_end, stripe_price_id, environment,
               stripe_customer_id, stripe_subscription_id, cancel_at_period_end
        FROM subscriptions
        WHERE user_id = :user_id
    """), {"user_id": user.id}).fetchone()

    return user, subscription


@router.get("/plans")
def get_plans():
    def is_plan_configured(plan_id: str, plan: dict):
        if plan_id == "free":
            return True
        return bool(os.getenv(plan["price_env"] or "")) or any(
            os.getenv(get_price_env(plan_id, interval) or "")
            for interval in PLAN_INTERVALS
        )

    return {
        "plans": [
            {
                "id": plan_id,
                "name": plan["name"],
                "description": plan["description"],
                "configured": is_plan_configured(plan_id, plan),
                "prices": {
                    interval: {
                        "configured": bool(
                            os.getenv(get_price_env(plan_id, interval) or "")
                        ),
                        "price_env": get_price_env(plan_id, interval),
                    }
                    for interval in PLAN_INTERVALS
                    if plan_id != "free"
                },
                "founder_prices": {
                    interval: {
                        "configured": bool(
                            os.getenv(get_price_env(plan_id, interval, founder=True) or "")
                        ),
                        "price_env": get_price_env(plan_id, interval, founder=True),
                    }
                    for interval in PLAN_INTERVALS
                    if plan_id != "free"
                },
            }
            for plan_id, plan in PLANS.items()
        ]
    }


@router.get("/config")
def billing_config():
    def is_plan_configured(plan_id: str, plan: dict):
        if plan_id == "free":
            return True
        return bool(os.getenv(plan["price_env"] or "")) or any(
            os.getenv(get_price_env(plan_id, interval) or "")
            for interval in PLAN_INTERVALS
        )

    return {
        "mode": os.getenv("STRIPE_MODE", "sandbox"),
        "stripe_ready": bool(stripe.api_key),
        "plans": {
            plan_id: {
                "configured": is_plan_configured(plan_id, plan),
                "price_env": plan["price_env"],
                "prices": {
                    interval: {
                        "configured": bool(
                            os.getenv(get_price_env(plan_id, interval) or "")
                        ),
                        "price_env": get_price_env(plan_id, interval),
                    }
                    for interval in PLAN_INTERVALS
                    if plan_id != "free"
                },
                "founder_prices": {
                    interval: {
                        "configured": bool(
                            os.getenv(get_price_env(plan_id, interval, founder=True) or "")
                        ),
                        "price_env": get_price_env(plan_id, interval, founder=True),
                    }
                    for interval in PLAN_INTERVALS
                    if plan_id != "free"
                },
            }
            for plan_id, plan in PLANS.items()
        },
        "webhook_ready": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
    }


@router.get("/current-subscription")
def current_subscription(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_billing_tables(conn)

        user, subscription = get_user_subscription(conn, email)

    if not subscription:
        return {
            "plan": normalize_plan(user.plan),
            "status": "free",
            "founder": {
                "is_founder": bool(user.is_founder),
                "tier": user.founder_tier,
                "discount": int(user.founder_discount or 0),
            },
            "current_period_end": None,
        }

    effective_plan = resolve_effective_plan(
        user.plan,
        subscription.plan,
        subscription.status,
    )

    return {
        "plan": effective_plan,
        "status": normalize_subscription_status(subscription.status),
        "subscription_plan": normalize_plan(subscription.plan),
        "user_plan": normalize_plan(user.plan),
        "stripe_price_id": subscription.stripe_price_id,
        "environment": subscription.environment or os.getenv("STRIPE_MODE", "sandbox"),
        "cancel_at_period_end": bool(subscription.cancel_at_period_end),
        "founder": {
            "is_founder": bool(user.is_founder),
            "tier": user.founder_tier,
            "discount": int(user.founder_discount or 0),
        },
        "current_period_end": (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
    }


@router.post("/create-checkout-session")
def create_checkout_session(data: dict, request: Request, email: str = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY manquant")

    plan_id = str(data.get("plan", "elite")).lower()
    interval = normalize_interval(data.get("interval") or data.get("billing_interval"))
    founder_checkout = bool(data.get("founder") or data.get("founder_plan"))
    plan, price_id, price_env, interval = get_plan_or_400(
        plan_id,
        interval=interval,
        founder=founder_checkout,
    )

    try:
        with engine.begin() as conn:
            ensure_billing_tables(conn)
            ensure_security_tables(conn)
            user, _ = get_user_subscription(conn, email)
            log_security_event(
                conn,
                "stripe_checkout_requested",
                request,
                email=email,
                user_id=user.id,
                metadata={
                    "plan": plan_id,
                    "interval": interval,
                    "founder_checkout": founder_checkout,
                    "price_env": price_env,
                },
            )

        discounts = []
        founder_coupon = os.getenv("STRIPE_FOUNDER_COUPON_ID")
        if bool(user.is_founder) and int(user.founder_discount or 0) > 0 and founder_coupon:
            discounts.append({"coupon": founder_coupon})

        session_kwargs = {
            "mode": "subscription",
            "customer_email": email,
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{FRONTEND_URL}/dashboard?checkout=success",
            "cancel_url": f"{FRONTEND_URL}/dashboard?checkout=cancel",
            "allow_promotion_codes": not bool(discounts),
            "metadata": {
                "email": email,
                "plan": plan_id,
                "interval": interval,
                "stripe_price_id": price_id,
                "price_env": price_env or "",
                "is_founder": str(bool(user.is_founder) or founder_checkout).lower(),
                "founder_checkout": str(founder_checkout).lower(),
                "founder_tier": user.founder_tier or "",
                "founder_discount": str(int(user.founder_discount or 0)),
            },
            "subscription_data": {
                "metadata": {
                    "email": email,
                    "plan": plan_id,
                    "interval": interval,
                    "stripe_price_id": price_id,
                    "price_env": price_env or "",
                    "is_founder": str(bool(user.is_founder) or founder_checkout).lower(),
                    "founder_checkout": str(founder_checkout).lower(),
                    "founder_tier": user.founder_tier or "",
                    "founder_discount": str(int(user.founder_discount or 0)),
                }
            },
        }
        if discounts:
            session_kwargs["discounts"] = discounts

        session = stripe.checkout.Session.create(**session_kwargs)
    except Exception as exc:
        capture_exception(exc, {"module": "billing", "operation": "checkout"})
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "url": session.url,
        "plan": plan["name"],
        "interval": interval,
        "founder": founder_checkout,
    }


@router.post("/customer-portal")
def create_customer_portal(email: str = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY manquant")

    with engine.begin() as conn:
        ensure_billing_tables(conn)
        _, subscription = get_user_subscription(conn, email)

    if not subscription or not subscription.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Customer Stripe introuvable")

    session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/dashboard?billing=portal",
    )

    return {"url": session.url}


@router.get("/billing-history")
def billing_history(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_billing_tables(conn)
        user, _ = get_user_subscription(conn, email)
        invoices = conn.execute(text("""
            SELECT stripe_invoice_id, amount_due, amount_paid, currency, status,
                   hosted_invoice_url, created_at
            FROM billing_invoices
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 24
        """), {"user_id": user.id}).fetchall()

    return {
        "invoices": [
            {
                "id": row.stripe_invoice_id,
                "amount_due": row.amount_due,
                "amount_paid": row.amount_paid,
                "currency": row.currency,
                "status": row.status,
                "url": row.hosted_invoice_url,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in invoices
        ]
    }


@router.post("/cancel-subscription")
def cancel_subscription(email: str = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY manquant")

    with engine.begin() as conn:
        ensure_billing_tables(conn)
        _, subscription = get_user_subscription(conn, email)

    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="Subscription Stripe introuvable")

    stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        cancel_at_period_end=True,
    )

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE subscriptions
            SET cancel_at_period_end = TRUE, updated_at = NOW()
            WHERE stripe_subscription_id = :stripe_subscription_id
        """), {"stripe_subscription_id": subscription.stripe_subscription_id})

    return {"status": "cancel_at_period_end"}


@router.post("/reactivate-subscription")
def reactivate_subscription(email: str = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY manquant")

    with engine.begin() as conn:
        ensure_billing_tables(conn)
        _, subscription = get_user_subscription(conn, email)

    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="Subscription Stripe introuvable")

    stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        cancel_at_period_end=False,
    )

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE subscriptions
            SET cancel_at_period_end = FALSE, updated_at = NOW()
            WHERE stripe_subscription_id = :stripe_subscription_id
        """), {"stripe_subscription_id": subscription.stripe_subscription_id})

    return {"status": "active"}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if os.getenv("STRIPE_MODE", "sandbox").lower() == "production" and not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook Stripe non configure")

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=webhook_secret,
            )
        else:
            event = stripe.Event.construct_from(
                await request.json(),
                stripe.api_key,
            )
    except Exception as exc:
        capture_exception(exc, {"module": "billing", "operation": "webhook"})
        raise HTTPException(status_code=400, detail=str(exc))

    with engine.begin() as conn:
        ensure_billing_tables(conn)
        ensure_security_tables(conn)
        result = conn.execute(text("""
            INSERT INTO subscription_events (stripe_event_id, event_type, status, payload)
            VALUES (:stripe_event_id, :event_type, :status, :payload)
            ON CONFLICT (stripe_event_id) DO NOTHING
        """), {
            "stripe_event_id": event.get("id"),
            "event_type": event.get("type"),
            "status": "received",
            "payload": str(event)[:8000],
        })
        if result.rowcount == 0:
            log_security_event(
                conn,
                "stripe_webhook_replay_ignored",
                request,
                severity="warning",
                metadata={"event_id": event.get("id"), "event_type": event.get("type")},
            )
            return {"received": True, "duplicate": True}
        log_security_event(
            conn,
            "stripe_webhook_received",
            request,
            metadata={"event_id": event.get("id"), "event_type": event.get("type")},
        )

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {}) or {}
        email = metadata.get("email") or session.get("customer_email")
        plan = str(metadata.get("plan") or "").lower()
        founder_checkout = str(metadata.get("founder_checkout") or "").lower() == "true"

        if email and plan:
            internal_status = normalize_subscription_status("active")
            with engine.begin() as conn:
                ensure_billing_tables(conn)
                user = conn.execute(text("""
                    SELECT id
                    FROM users
                    WHERE email = :email
                """), {"email": email}).fetchone()

                conn.execute(text("""
                    UPDATE users
                    SET plan = :plan,
                        is_founder = CASE WHEN :founder_checkout THEN TRUE ELSE is_founder END,
                        founder_tier = CASE WHEN :founder_checkout THEN :founder_tier ELSE founder_tier END
                    WHERE email = :email
                """), {
                    "plan": plan.upper(),
                    "founder_checkout": founder_checkout,
                    "founder_tier": plan.upper(),
                    "email": email,
                })

                if user:
                    conn.execute(text("""
                    INSERT INTO subscriptions (
                            user_id,
                            plan,
                            status,
                            stripe_customer_id,
                            stripe_subscription_id,
                            stripe_price_id,
                            environment,
                            updated_at
                        )
                        VALUES (
                            :user_id,
                            :plan,
                            :status,
                            :stripe_customer_id,
                            :stripe_subscription_id,
                            :stripe_price_id,
                            :environment,
                            NOW()
                        )
                        ON CONFLICT (user_id)
                        DO UPDATE SET
                            plan = EXCLUDED.plan,
                            status = EXCLUDED.status,
                            stripe_customer_id = EXCLUDED.stripe_customer_id,
                            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                            stripe_price_id = EXCLUDED.stripe_price_id,
                            environment = EXCLUDED.environment,
                            updated_at = NOW()
                    """), {
                        "user_id": user.id,
                        "plan": plan.upper(),
                        "status": internal_status,
                        "stripe_customer_id": session.get("customer"),
                        "stripe_subscription_id": session.get("subscription"),
                        "stripe_price_id": session.get("metadata", {}).get("stripe_price_id")
                        or os.getenv(PLANS.get(plan, {}).get("price_env") or ""),
                        "environment": os.getenv("STRIPE_MODE", "sandbox"),
                    })

                invalidate_subscription_caches(email, user.id if user else None)
                if user:
                    capture_event(
                        conn,
                        FOUNDER_UPGRADE if bool(session.get("metadata", {}).get("is_founder") == "true") else SUBSCRIPTION_UPGRADED,
                        user_id=user.id,
                        email=email,
                        properties={"plan": plan.upper(), "stripe_event": event.get("id")},
                    )
                logger.info(
                    "subscription_change event=checkout_completed email=%s user_id=%s plan=%s status=%s",
                    email,
                    user.id if user else None,
                    plan.upper(),
                    internal_status,
                )

    if event["type"] in ["customer.subscription.updated", "customer.subscription.deleted"]:
        subscription = event["data"]["object"]
        stripe_subscription_id = subscription.get("id")
        status = normalize_subscription_status(subscription.get("status"))
        if event["type"] == "customer.subscription.deleted":
            status = "canceled"
        cancel_at_period_end = bool(subscription.get("cancel_at_period_end"))
        price_id = None
        try:
            price_id = subscription.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
        except Exception:
            price_id = None
        next_plan = plan_from_price_id(price_id)

        with engine.begin() as conn:
            ensure_billing_tables(conn)
            current = conn.execute(text("""
                SELECT users.email, users.id
                FROM subscriptions
                JOIN users ON users.id = subscriptions.user_id
                WHERE subscriptions.stripe_subscription_id = :stripe_subscription_id
            """), {
                "stripe_subscription_id": stripe_subscription_id,
            }).fetchone()

            conn.execute(text("""
                UPDATE subscriptions
                SET plan = COALESCE(:plan, plan),
                    status = :status,
                    cancel_at_period_end = :cancel_at_period_end,
                    updated_at = NOW()
                WHERE stripe_subscription_id = :stripe_subscription_id
            """), {
                "plan": next_plan,
                "status": status,
                "cancel_at_period_end": cancel_at_period_end,
                "stripe_subscription_id": stripe_subscription_id,
            })

            if current and next_plan and status in ["active", "trialing", "past_due"]:
                conn.execute(text("""
                    UPDATE users
                    SET plan = :plan
                    WHERE id = :user_id
                """), {"plan": next_plan, "user_id": current.id})

            if current and event["type"] == "customer.subscription.deleted":
                conn.execute(text("""
                    UPDATE users
                    SET plan = 'FREE'
                    WHERE id = :user_id
                """), {"user_id": current.id})

            invalidate_subscription_caches(
                current.email if current else None,
                current.id if current else None,
            )
            logger.info(
                "subscription_change event=%s user_id=%s plan=%s status=%s stripe_subscription_id=%s",
                event["type"],
                current.id if current else None,
                next_plan,
                status,
                stripe_subscription_id,
            )

    if event["type"] in ["invoice.paid", "invoice.payment_failed"]:
        invoice = event["data"]["object"]
        with engine.begin() as conn:
            ensure_billing_tables(conn)
            subscription = conn.execute(text("""
                SELECT user_id
                FROM subscriptions
                WHERE stripe_subscription_id = :stripe_subscription_id
                   OR stripe_customer_id = :stripe_customer_id
            """), {
                "stripe_subscription_id": invoice.get("subscription"),
                "stripe_customer_id": invoice.get("customer"),
            }).fetchone()

            conn.execute(text("""
                INSERT INTO billing_invoices (
                    user_id, stripe_invoice_id, stripe_customer_id,
                    stripe_subscription_id, amount_due, amount_paid,
                    currency, status, hosted_invoice_url, updated_at
                )
                VALUES (
                    :user_id, :stripe_invoice_id, :stripe_customer_id,
                    :stripe_subscription_id, :amount_due, :amount_paid,
                    :currency, :status, :hosted_invoice_url, NOW()
                )
                ON CONFLICT (stripe_invoice_id)
                DO UPDATE SET
                    amount_due = EXCLUDED.amount_due,
                    amount_paid = EXCLUDED.amount_paid,
                    status = EXCLUDED.status,
                    hosted_invoice_url = EXCLUDED.hosted_invoice_url,
                    updated_at = NOW()
            """), {
                "user_id": subscription.user_id if subscription else None,
                "stripe_invoice_id": invoice.get("id"),
                "stripe_customer_id": invoice.get("customer"),
                "stripe_subscription_id": invoice.get("subscription"),
                "amount_due": invoice.get("amount_due") or 0,
                "amount_paid": invoice.get("amount_paid") or 0,
                "currency": invoice.get("currency") or "eur",
                "status": invoice.get("status"),
                "hosted_invoice_url": invoice.get("hosted_invoice_url"),
            })

    return {"received": True}
