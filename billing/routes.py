import os
import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from auth.utils import get_current_user
from core.cache import delete_cache_keys, delete_cache_patterns
from database import engine
from product.entitlements import build_entitlements, normalize_plan, plan_rank, resolve_effective_plan
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
        "description": "Decouverte: Wealth Snapshot, prochain palier, Future Intelligence reduite et Ethan limite.",
    },
    "gold": {
        "name": "Gold - Growth",
        "price_env": "STRIPE_PRICE_GOLD",
        "description": "Trajectoire active: Ethan flottant, patrimoine activable, Future Intelligence, Decision Intelligence et scorecard simple.",
    },
    "elite": {
        "name": "Elite - Wealth OS",
        "price_env": "STRIPE_PRICE_ELITE",
        "description": "Optimisation: Family Office CEO, recit enrichi, stress tests avances, dependances et simulations multi-scenarios.",
    },
    "liberty": {
        "name": "Liberty - Financial Freedom",
        "price_env": "STRIPE_PRICE_LIBERTY",
        "description": "Arbitrages Family Office: comptes enfants, objectifs avances, board virtuel, transmission et priorites d'allocation.",
    },
    "legacy": {
        "name": "Dynasty - Family Office",
        "price_env": "STRIPE_PRICE_LEGACY",
        "description": "Dynasty Office: gouvernance familiale, protection, vault, heritiers et strategie generationnelle.",
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
            f"product:{email}*",
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


def stripe_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError):
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
    conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pending_plan TEXT"))
    conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pending_stripe_price_id TEXT"))
    conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pending_effective_at TIMESTAMP"))
    conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pending_change_type TEXT"))
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
               stripe_customer_id, stripe_subscription_id, cancel_at_period_end,
               pending_plan, pending_stripe_price_id, pending_effective_at,
               pending_change_type
        FROM subscriptions
        WHERE user_id = :user_id
    """), {"user_id": user.id}).fetchone()

    return user, subscription


def stripe_value(obj, key: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def stripe_nested_value(obj, *keys, default=None):
    current = obj
    for key in keys:
        if current is None:
            return default
        if isinstance(key, int):
            try:
                current = current[key]
            except (IndexError, KeyError, TypeError):
                return default
            continue
        current = stripe_value(current, key, default)
    return default if current is None else current


def stripe_object_id(value):
    if not value:
        return None
    if isinstance(value, str):
        return value
    return stripe_value(value, "id")


def normalize_subscription_event(event_type: str, stripe_object):
    subscription_id = stripe_value(stripe_object, "id")
    status = normalize_subscription_status(stripe_value(stripe_object, "status"))

    if event_type == "customer.subscription.deleted":
        status = "canceled"
    if event_type == "customer.subscription.paused":
        status = "paused"

    price_id = stripe_nested_value(stripe_object, "items", "data", 0, "price", "id")
    plan = plan_from_price_id(price_id)

    return {
        "event_type": "SUBSCRIPTION_UPDATED",
        "stripe_customer_id": stripe_value(stripe_object, "customer"),
        "stripe_subscription_id": subscription_id,
        "stripe_price_id": price_id,
        "plan": plan,
        "status": status,
        "cancel_at_period_end": bool(stripe_value(stripe_object, "cancel_at_period_end")),
        "current_period_end": stripe_timestamp(stripe_value(stripe_object, "current_period_end")),
    }


def normalize_checkout_event(session):
    metadata = stripe_value(session, "metadata", {}) or {}
    plan = str(stripe_value(metadata, "plan") or "").upper() or None
    return {
        "event_type": "CHECKOUT_COMPLETED",
        "email": stripe_value(metadata, "email") or stripe_value(session, "customer_email"),
        "stripe_customer_id": stripe_value(session, "customer"),
        "stripe_subscription_id": stripe_value(session, "subscription"),
        "stripe_price_id": stripe_value(metadata, "stripe_price_id"),
        "plan": normalize_plan(plan) if plan else None,
        "status": "active",
        "cancel_at_period_end": False,
        "current_period_end": None,
        "founder_checkout": str(stripe_value(metadata, "founder_checkout") or "").lower() == "true",
    }


def find_subscription_user(conn, event: dict):
    if event.get("email"):
        user = conn.execute(text("""
            SELECT id, email
            FROM users
            WHERE email = :email
        """), {"email": event["email"]}).fetchone()
        if user:
            return user

    if event.get("stripe_subscription_id"):
        user = conn.execute(text("""
            SELECT users.id, users.email
            FROM subscriptions
            JOIN users ON users.id = subscriptions.user_id
            WHERE subscriptions.stripe_subscription_id = :stripe_subscription_id
        """), {"stripe_subscription_id": event["stripe_subscription_id"]}).fetchone()
        if user:
            return user

    if event.get("stripe_customer_id"):
        user = conn.execute(text("""
            SELECT users.id, users.email
            FROM subscriptions
            JOIN users ON users.id = subscriptions.user_id
            WHERE subscriptions.stripe_customer_id = :stripe_customer_id
        """), {"stripe_customer_id": event["stripe_customer_id"]}).fetchone()
        if user:
            return user

    return None


def update_subscription_state(conn, event: dict):
    user = find_subscription_user(conn, event)
    if not user:
        logger.warning(
            "billing_subscription_event_without_user event_type=%s customer=%s subscription=%s email=%s",
            event.get("event_type"),
            event.get("stripe_customer_id"),
            event.get("stripe_subscription_id"),
            event.get("email"),
        )
        return None

    current_subscription = conn.execute(text("""
        SELECT plan, pending_plan
        FROM subscriptions
        WHERE user_id = :user_id
    """), {"user_id": user.id}).fetchone()

    status = normalize_subscription_status(event.get("status"))
    plan = normalize_plan(
        event.get("plan")
        or (current_subscription.plan if current_subscription else None)
        or "FREE"
    )
    active_status = status in {"active", "trialing", "past_due"}
    effective_user_plan = plan if active_status else "FREE"

    conn.execute(text("""
        INSERT INTO subscriptions (
            user_id, plan, status, stripe_customer_id, stripe_subscription_id,
            stripe_price_id, current_period_end, environment,
            cancel_at_period_end, updated_at
        )
        VALUES (
            :user_id, :plan, :status, :stripe_customer_id, :stripe_subscription_id,
            :stripe_price_id, :current_period_end, :environment,
            :cancel_at_period_end, NOW()
        )
        ON CONFLICT (user_id)
        DO UPDATE SET
            plan = EXCLUDED.plan,
            status = EXCLUDED.status,
            stripe_customer_id = COALESCE(EXCLUDED.stripe_customer_id, subscriptions.stripe_customer_id),
            stripe_subscription_id = COALESCE(EXCLUDED.stripe_subscription_id, subscriptions.stripe_subscription_id),
            stripe_price_id = COALESCE(EXCLUDED.stripe_price_id, subscriptions.stripe_price_id),
            current_period_end = COALESCE(EXCLUDED.current_period_end, subscriptions.current_period_end),
            environment = EXCLUDED.environment,
            cancel_at_period_end = EXCLUDED.cancel_at_period_end,
            pending_plan = CASE
                WHEN EXCLUDED.status NOT IN ('active', 'trialing', 'past_due') THEN NULL
                WHEN subscriptions.pending_plan IS NOT NULL AND EXCLUDED.plan = subscriptions.pending_plan THEN NULL
                ELSE subscriptions.pending_plan
            END,
            pending_stripe_price_id = CASE
                WHEN EXCLUDED.status NOT IN ('active', 'trialing', 'past_due') THEN NULL
                WHEN subscriptions.pending_plan IS NOT NULL AND EXCLUDED.plan = subscriptions.pending_plan THEN NULL
                ELSE subscriptions.pending_stripe_price_id
            END,
            pending_effective_at = CASE
                WHEN EXCLUDED.status NOT IN ('active', 'trialing', 'past_due') THEN NULL
                WHEN subscriptions.pending_plan IS NOT NULL AND EXCLUDED.plan = subscriptions.pending_plan THEN NULL
                ELSE subscriptions.pending_effective_at
            END,
            pending_change_type = CASE
                WHEN EXCLUDED.status NOT IN ('active', 'trialing', 'past_due') THEN NULL
                WHEN subscriptions.pending_plan IS NOT NULL AND EXCLUDED.plan = subscriptions.pending_plan THEN NULL
                ELSE subscriptions.pending_change_type
            END,
            updated_at = NOW()
    """), {
        "user_id": user.id,
        "plan": plan,
        "status": status,
        "stripe_customer_id": event.get("stripe_customer_id"),
        "stripe_subscription_id": event.get("stripe_subscription_id"),
        "stripe_price_id": event.get("stripe_price_id"),
        "current_period_end": event.get("current_period_end"),
        "environment": os.getenv("STRIPE_MODE", "sandbox"),
        "cancel_at_period_end": bool(event.get("cancel_at_period_end")),
    })

    conn.execute(text("""
        UPDATE users
        SET plan = :plan,
            is_founder = CASE WHEN :founder_checkout THEN TRUE ELSE is_founder END,
            founder_tier = CASE WHEN :founder_checkout THEN :founder_tier ELSE founder_tier END
        WHERE id = :user_id
    """), {
        "plan": effective_user_plan,
        "founder_checkout": bool(event.get("founder_checkout")),
        "founder_tier": plan if event.get("founder_checkout") else None,
        "user_id": user.id,
    })

    if event.get("event_type") == "CHECKOUT_COMPLETED":
        conn.execute(text("""
            UPDATE subscriptions
            SET pending_plan = NULL,
                pending_stripe_price_id = NULL,
                pending_effective_at = NULL,
                pending_change_type = NULL,
                cancel_at_period_end = FALSE,
                updated_at = NOW()
            WHERE user_id = :user_id
        """), {"user_id": user.id})

    invalidate_subscription_caches(user.email, user.id)
    logger.info(
        "subscription_state_updated event_type=%s user_id=%s plan=%s status=%s effective_plan=%s",
        event.get("event_type"),
        user.id,
        plan,
        status,
        effective_user_plan,
    )
    return user


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
                "entitlements": build_entitlements(plan_id.upper()),
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
                "entitlements": build_entitlements(plan_id.upper()),
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
            "pending_plan": None,
            "pending_effective_at": None,
            "pending_change_type": None,
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
        "pending_plan": normalize_plan(subscription.pending_plan) if subscription.pending_plan else None,
        "pending_effective_at": (
            subscription.pending_effective_at.isoformat()
            if subscription.pending_effective_at
            else None
        ),
        "pending_change_type": subscription.pending_change_type,
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


@router.post("/schedule-downgrade")
def schedule_downgrade(data: dict, request: Request, email: str = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY manquant")

    target_plan = normalize_plan(data.get("plan"))
    interval = normalize_interval(data.get("interval") or data.get("billing_interval"))
    if target_plan == "FREE":
        target_plan_id = "free"
    else:
        target_plan_id = target_plan.lower()

    with engine.begin() as conn:
        ensure_billing_tables(conn)
        ensure_security_tables(conn)
        user, subscription = get_user_subscription(conn, email)

        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(status_code=400, detail="Subscription Stripe introuvable")

        current_plan = resolve_effective_plan(
            user.plan,
            subscription.plan,
            subscription.status,
        )

        if plan_rank(target_plan) >= plan_rank(current_plan):
            raise HTTPException(
                status_code=400,
                detail="Ce flux est reserve aux changements vers un plan inferieur.",
            )

        log_security_event(
            conn,
            "stripe_downgrade_requested",
            request,
            email=email,
            user_id=user.id,
            metadata={
                "current_plan": current_plan,
                "target_plan": target_plan,
                "interval": interval,
            },
        )

    try:
        stripe_subscription = stripe.Subscription.retrieve(
            subscription.stripe_subscription_id,
            expand=["items.data.price"],
        )
        current_period_end = stripe_timestamp(
            stripe_value(stripe_subscription, "current_period_end")
        ) or subscription.current_period_end

        if target_plan == "FREE":
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
                metadata={
                    "pending_plan": "FREE",
                    "pending_change_type": "cancel",
                },
            )
            pending_price_id = None
            change_type = "cancel"
        else:
            _, target_price_id, price_env, interval = get_plan_or_400(
                target_plan_id,
                interval=interval,
                founder=bool(user.is_founder),
            )
            item = stripe_nested_value(stripe_subscription, "items", "data", 0)
            current_price_id = stripe_nested_value(item, "price", "id")
            quantity = stripe_value(item, "quantity", 1) or 1
            if not item or not current_price_id:
                raise HTTPException(
                    status_code=400,
                    detail="Impossible de lire la ligne d'abonnement Stripe.",
                )

            current_period_start = stripe_value(stripe_subscription, "current_period_start")
            current_period_end_raw = stripe_value(stripe_subscription, "current_period_end")
            schedule_ref = stripe_object_id(stripe_value(stripe_subscription, "schedule"))
            if schedule_ref:
                schedule = stripe.SubscriptionSchedule.retrieve(schedule_ref)
            else:
                schedule = stripe.SubscriptionSchedule.create(
                    from_subscription=subscription.stripe_subscription_id
                )

            schedule_id = stripe_object_id(schedule)
            current_phase = stripe_nested_value(schedule, "phases", 0, default={})
            phase_start = stripe_value(current_phase, "start_date") or current_period_start
            stripe.SubscriptionSchedule.modify(
                schedule_id,
                end_behavior="release",
                phases=[
                    {
                        "items": [{"price": current_price_id, "quantity": quantity}],
                        "start_date": phase_start,
                        "end_date": current_period_end_raw,
                    },
                    {
                        "items": [{"price": target_price_id, "quantity": quantity}],
                    },
                ],
                metadata={
                    "pending_plan": target_plan,
                    "pending_change_type": "downgrade",
                    "pending_price_env": price_env or "",
                },
            )
            pending_price_id = target_price_id
            change_type = "downgrade"

        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE subscriptions
                SET pending_plan = :pending_plan,
                    pending_stripe_price_id = :pending_stripe_price_id,
                    pending_effective_at = :pending_effective_at,
                    pending_change_type = :pending_change_type,
                    cancel_at_period_end = :cancel_at_period_end,
                    current_period_end = COALESCE(:pending_effective_at, current_period_end),
                    updated_at = NOW()
                WHERE stripe_subscription_id = :stripe_subscription_id
            """), {
                "pending_plan": target_plan,
                "pending_stripe_price_id": pending_price_id,
                "pending_effective_at": current_period_end,
                "pending_change_type": change_type,
                "cancel_at_period_end": target_plan == "FREE",
                "stripe_subscription_id": subscription.stripe_subscription_id,
            })
            invalidate_subscription_caches(email, user.id)

    except HTTPException:
        raise
    except Exception as exc:
        capture_exception(exc, {"module": "billing", "operation": "schedule_downgrade"})
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "scheduled",
        "current_plan": current_plan,
        "pending_plan": target_plan,
        "pending_effective_at": current_period_end.isoformat() if current_period_end else None,
        "change_type": change_type,
    }


@router.post("/customer-portal")
def create_customer_portal(email: str = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY manquant")

    with engine.begin() as conn:
        ensure_billing_tables(conn)
        user, subscription = get_user_subscription(conn, email)

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
            SET cancel_at_period_end = TRUE,
                pending_plan = 'FREE',
                pending_stripe_price_id = NULL,
                pending_effective_at = current_period_end,
                pending_change_type = 'cancel',
                updated_at = NOW()
            WHERE stripe_subscription_id = :stripe_subscription_id
        """), {"stripe_subscription_id": subscription.stripe_subscription_id})
        invalidate_subscription_caches(email, user.id)

    return {"status": "cancel_at_period_end"}


@router.post("/reactivate-subscription")
def reactivate_subscription(email: str = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY manquant")

    with engine.begin() as conn:
        ensure_billing_tables(conn)
        user, subscription = get_user_subscription(conn, email)

    if not subscription or not subscription.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="Subscription Stripe introuvable")

    stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        cancel_at_period_end=False,
    )

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE subscriptions
            SET cancel_at_period_end = FALSE,
                pending_plan = NULL,
                pending_stripe_price_id = NULL,
                pending_effective_at = NULL,
                pending_change_type = NULL,
                updated_at = NOW()
            WHERE stripe_subscription_id = :stripe_subscription_id
        """), {"stripe_subscription_id": subscription.stripe_subscription_id})
        invalidate_subscription_caches(email, user.id)

    return {"status": "active"}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook Stripe non configure")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=webhook_secret,
        )
    except Exception as exc:
        capture_exception(exc, {"module": "billing", "operation": "webhook"})
        raise HTTPException(status_code=400, detail=str(exc))

    event_id = event.id
    event_type = event.type

    with engine.begin() as conn:
        ensure_billing_tables(conn)
        ensure_security_tables(conn)
        result = conn.execute(text("""
            INSERT INTO subscription_events (stripe_event_id, event_type, status, payload)
            VALUES (:stripe_event_id, :event_type, :status, :payload)
            ON CONFLICT (stripe_event_id) DO NOTHING
        """), {
            "stripe_event_id": event_id,
            "event_type": event_type,
            "status": "received",
            "payload": str(event)[:8000],
        })
        if result.rowcount == 0:
            log_security_event(
                conn,
                "stripe_webhook_replay_ignored",
                request,
                severity="warning",
                metadata={"event_id": event_id, "event_type": event_type},
            )
            return {"received": True, "duplicate": True}
        log_security_event(
            conn,
            "stripe_webhook_received",
            request,
            metadata={"event_id": event_id, "event_type": event_type},
        )

    subscription_events = {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "customer.subscription.paused",
    }

    if event_type in subscription_events:
        normalized_event = (
            normalize_checkout_event(event.data.object)
            if event_type == "checkout.session.completed"
            else normalize_subscription_event(event_type, event.data.object)
        )

        with engine.begin() as conn:
            ensure_billing_tables(conn)
            user = update_subscription_state(conn, normalized_event)
            conn.execute(text("""
                UPDATE subscription_events
                SET user_id = :user_id,
                    plan = :plan,
                    status = :status
                WHERE stripe_event_id = :stripe_event_id
            """), {
                "user_id": user.id if user else None,
                "plan": normalized_event.get("plan"),
                "status": normalized_event.get("status"),
                "stripe_event_id": event_id,
            })

            if user and event_type == "checkout.session.completed":
                capture_event(
                    conn,
                    FOUNDER_UPGRADE
                    if bool(normalized_event.get("founder_checkout"))
                    else SUBSCRIPTION_UPGRADED,
                    user_id=user.id,
                    email=user.email,
                    properties={
                        "plan": normalized_event.get("plan"),
                        "stripe_event": event_id,
                    },
                )

    if event_type in ["invoice.paid", "invoice.payment_failed"]:
        invoice = event.data.object
        with engine.begin() as conn:
            ensure_billing_tables(conn)
            subscription = conn.execute(text("""
                SELECT subscriptions.user_id, users.email
                FROM subscriptions
                JOIN users ON users.id = subscriptions.user_id
                WHERE stripe_subscription_id = :stripe_subscription_id
                   OR stripe_customer_id = :stripe_customer_id
            """), {
                "stripe_subscription_id": stripe_value(invoice, "subscription"),
                "stripe_customer_id": stripe_value(invoice, "customer"),
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
                "stripe_invoice_id": stripe_value(invoice, "id"),
                "stripe_customer_id": stripe_value(invoice, "customer"),
                "stripe_subscription_id": stripe_value(invoice, "subscription"),
                "amount_due": stripe_value(invoice, "amount_due") or 0,
                "amount_paid": stripe_value(invoice, "amount_paid") or 0,
                "currency": stripe_value(invoice, "currency") or "eur",
                "status": stripe_value(invoice, "status"),
                "hosted_invoice_url": stripe_value(invoice, "hosted_invoice_url"),
            })

            if subscription:
                next_status = "active" if event_type == "invoice.paid" else "past_due"
                conn.execute(text("""
                    UPDATE subscriptions
                    SET status = :status,
                        updated_at = NOW()
                    WHERE user_id = :user_id
                """), {
                    "status": next_status,
                    "user_id": subscription.user_id,
                })
                invalidate_subscription_caches(subscription.email, subscription.user_id)

    if event_type == "customer.deleted":
        customer = event.data.object
        with engine.begin() as conn:
            ensure_billing_tables(conn)
            current = conn.execute(text("""
                SELECT subscriptions.user_id, users.email
                FROM subscriptions
                JOIN users ON users.id = subscriptions.user_id
                WHERE subscriptions.stripe_customer_id = :stripe_customer_id
            """), {"stripe_customer_id": stripe_value(customer, "id")}).fetchone()

            if current:
                conn.execute(text("""
                    UPDATE subscriptions
                    SET status = 'canceled',
                        plan = 'FREE',
                        pending_plan = NULL,
                        pending_stripe_price_id = NULL,
                        pending_effective_at = NULL,
                        pending_change_type = NULL,
                        updated_at = NOW()
                    WHERE user_id = :user_id
                """), {"user_id": current.user_id})
                conn.execute(text("""
                    UPDATE users
                    SET plan = 'FREE'
                    WHERE id = :user_id
                """), {"user_id": current.user_id})
                invalidate_subscription_caches(current.email, current.user_id)

    return {"received": True}
