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
            SELECT plan, status, current_period_end
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
                            updated_at
                        )
                        VALUES (
                            :user_id,
                            :plan,
                            'active',
                            :stripe_customer_id,
                            :stripe_subscription_id,
                            NOW()
                        )
                        ON CONFLICT (user_id)
                        DO UPDATE SET
                            plan = EXCLUDED.plan,
                            status = EXCLUDED.status,
                            stripe_customer_id = EXCLUDED.stripe_customer_id,
                            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                            updated_at = NOW()
                    """), {
                        "user_id": user.id,
                        "plan": plan.upper(),
                        "stripe_customer_id": session.get("customer"),
                        "stripe_subscription_id": session.get("subscription"),
                    })

    return {"received": True}
