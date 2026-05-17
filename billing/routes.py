import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text

from auth.utils import get_current_user
from database import engine


router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://vision-business.com")

PLANS = {
    "gold": {
        "name": "Gold",
        "price_env": "STRIPE_PRICE_GOLD",
        "description": "Optimisation avancee et opportunites personnalisees.",
    },
    "elite": {
        "name": "Elite",
        "price_env": "STRIPE_PRICE_ELITE",
        "description": "Pilotage patrimonial avance et intelligence premium.",
    },
    "liberty": {
        "name": "Liberty",
        "price_env": "STRIPE_PRICE_LIBERTY",
        "description": "Atteindre et piloter la liberte financiere.",
    },
    "liberty_legacy": {
        "name": "Liberty Legacy",
        "price_env": "STRIPE_PRICE_LIBERTY_LEGACY",
        "description": (
            "Conserver, multiplier et transmettre la liberte financiere "
            "a sa famille."
        ),
    },
}


def get_plan_or_400(plan_id: str):
    plan = PLANS.get(plan_id)

    if not plan:
        raise HTTPException(status_code=400, detail="Plan inconnu")

    price_id = os.getenv(plan["price_env"])

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
                "configured": bool(os.getenv(plan["price_env"])),
            }
            for plan_id, plan in PLANS.items()
        ]
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
                conn.execute(text("""
                    UPDATE users
                    SET plan = :plan
                    WHERE email = :email
                """), {"plan": plan.upper(), "email": email})

    return {"received": True}

