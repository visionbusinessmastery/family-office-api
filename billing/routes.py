import os
import stripe
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database import engine
from auth.utils import get_current_user

router = APIRouter()

# =========================
# CONFIG STRIPE
# =========================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe.api_key:
    print("⚠️ STRIPE NOT CONFIGURED (billing disabled)")


FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# =========================
# CREATE CHECKOUT SESSION
# =========================
@router.post("/checkout")
def create_checkout(plan: str, email: str = get_current_user):

    try:
        # mapping plans → Stripe price IDs
        prices = {
            "GOLD": os.getenv("STRIPE_PRICE_GOLD"),
            "VIP": os.getenv("STRIPE_PRICE_VIP"),
        }

        if plan not in prices:
            raise HTTPException(status_code=400, detail="Plan invalide")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=email,
            line_items=[
                {
                    "price": prices[plan],
                    "quantity": 1,
                }
            ],
            success_url=f"{FRONTEND_URL}/dashboard?payment=success",
            cancel_url=f"{FRONTEND_URL}/dashboard?payment=cancel",
        )

        return {"url": session.url}

    except Exception as e:
        print("STRIPE ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Stripe error")


# =========================
# WEBHOOK (OPTIONNEL MAIS IMPORTANT)
# =========================
@router.post("/webhook")
async def stripe_webhook(request):

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )

    except Exception as e:
        print("WEBHOOK ERROR:", str(e))
        raise HTTPException(status_code=400, detail="Webhook error")

    # =========================
    # SUBSCRIPTION SUCCESS
    # =========================
    if event["type"] == "checkout.session.completed":

        session = event["data"]["object"]
        email = session.get("customer_email")

        # upgrade user plan
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE users
                SET plan = 'GOLD'
                WHERE email = :email
            """), {"email": email})

        print("💳 USER UPGRADED:", email)

    return {"status": "ok"}
