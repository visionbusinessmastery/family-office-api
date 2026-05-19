import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from auth.utils import get_current_user
from database import engine


router = APIRouter()
_billing_schema_ready = False

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://vision-business.com")

PLANS = {
    "free": {
        "name": "Free - Foundation",
        "price_env": None,
        "description": "Fondations financieres, progression et IA simple.",
    },
    "gold": {
        "name": "Gold - Growth",
        "price_env": "STRIPE_PRICE_GOLD",
        "description": "Croissance patrimoniale, analytics, immobilier, opportunites et IA avancee.",
    },
    "elite": {
        "name": "Elite - Wealth OS",
        "price_env": "STRIPE_PRICE_ELITE",
        "description": "Family Office OS, multi-user, gouvernance, IA premium et consolidation.",
    },
}


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


def get_plan_or_400(plan_id: str):
    plan = PLANS.get(plan_id)

    if not plan or plan_id == "free":
        raise HTTPException(status_code=400, detail="Plan inconnu")

    price_id = os.getenv(plan["price_env"] or "")

    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"Price Stripe manquant: {plan['price_env']}",
        )

    return plan, price_id


@router.get("/plans")
def get_plans():
    return {
        "plans": [
            {
                "id": plan_id,
                "name": plan["name"],
                "description": plan["description"],
                "configured": plan_id == "free" or bool(os.getenv(plan["price_env"] or "")),
            }
            for plan_id, plan in PLANS.items()
        ]
    }


@router.get("/config")
def billing_config():
    return {
        "mode": os.getenv("STRIPE_MODE", "sandbox"),
        "stripe_ready": bool(stripe.api_key),
        "plans": {
            plan_id: {
                "configured": plan_id == "free" or bool(os.getenv(plan["price_env"] or "")),
                "price_env": plan["price_env"],
            }
            for plan_id, plan in PLANS.items()
        },
        "webhook_ready": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
    }


@router.get("/current-subscription")
def current_subscription(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_billing_tables(conn)

        user = conn.execute(text("""
            SELECT id, plan
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        subscription = conn.execute(text("""
            SELECT plan, status, current_period_end, stripe_price_id, environment
            FROM subscriptions
            WHERE user_id = :user_id
        """), {"user_id": user.id}).fetchone()

    if not subscription:
        return {
            "plan": (user.plan or "FREE").upper(),
            "status": "free",
            "current_period_end": None,
        }

    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "stripe_price_id": subscription.stripe_price_id,
        "environment": subscription.environment or os.getenv("STRIPE_MODE", "sandbox"),
        "current_period_end": (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
    }


@router.post("/create-checkout-session")
def create_checkout_session(data: dict, email: str = Depends(get_current_user)):
    if not stripe.api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY manquant")

    plan_id = data.get("plan", "elite")
    plan, price_id = get_plan_or_400(plan_id)

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{FRONTEND_URL}/dashboard?checkout=success",
            cancel_url=f"{FRONTEND_URL}/dashboard?checkout=cancel",
            metadata={
                "email": email,
                "plan": plan_id,
            },
            subscription_data={
                "metadata": {
                    "email": email,
                    "plan": plan_id,
                }
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"url": session.url, "plan": plan["name"]}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

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
        raise HTTPException(status_code=400, detail=str(exc))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("metadata", {}).get("email") or session.get("customer_email")
        plan = session.get("metadata", {}).get("plan")

        if email and plan:
            with engine.begin() as conn:
                ensure_billing_tables(conn)
                user = conn.execute(text("""
                    SELECT id
                    FROM users
                    WHERE email = :email
                """), {"email": email}).fetchone()

                conn.execute(text("""
                    UPDATE users
                    SET plan = :plan
                    WHERE email = :email
                """), {"plan": plan.upper(), "email": email})

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
                            'active',
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
                        "stripe_customer_id": session.get("customer"),
                        "stripe_subscription_id": session.get("subscription"),
                        "stripe_price_id": os.getenv(PLANS.get(plan, {}).get("price_env") or ""),
                        "environment": os.getenv("STRIPE_MODE", "sandbox"),
                    })

    if event["type"] in ["customer.subscription.updated", "customer.subscription.deleted"]:
        subscription = event["data"]["object"]
        stripe_subscription_id = subscription.get("id")
        status = subscription.get("status")
        cancel_at_period_end = bool(subscription.get("cancel_at_period_end"))

        with engine.begin() as conn:
            ensure_billing_tables(conn)
            conn.execute(text("""
                UPDATE subscriptions
                SET status = :status,
                    cancel_at_period_end = :cancel_at_period_end,
                    updated_at = NOW()
                WHERE stripe_subscription_id = :stripe_subscription_id
            """), {
                "status": status,
                "cancel_at_period_end": cancel_at_period_end,
                "stripe_subscription_id": stripe_subscription_id,
            })

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
