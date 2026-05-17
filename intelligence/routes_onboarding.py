# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# =========================
# HELPERS
# =========================
def get_user_id(conn, email: str):
    user = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    return user.id if user else None


# =========================
# UPDATE ONBOARDING
# =========================
@router.put("/")
def update_onboarding(data: dict, user=Depends(get_current_user)):

    email = user

    with engine.begin() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            return {"error": "User not found"}

        conn.execute(
            text("""
                UPDATE users
                SET revenus_mensuels = :revenus_mensuels,
                    charges_mensuelles = :charges_mensuelles
                WHERE id = :user_id
            """),
            {
                "user_id": user_id,
                "revenus_mensuels": data.get("revenus_mensuels", 0),
                "charges_mensuelles": data.get("charges_mensuelles", 0),
            }
        )

    return {"status": "updated"}


# sync onboarding → financial system

conn.execute(text("""
    INSERT INTO income_sources (user_id, name, income_type, monthly_income)
    VALUES (:uid, 'Onboarding income', 'manual', :income)
    ON CONFLICT DO NOTHING
"""), {
    "uid": user_id,
    "income": data.get("revenus_mensuels", 0)
})

conn.execute(text("""
    INSERT INTO debts (user_id, name, debt_type, remaining_amount, monthly_payment)
    VALUES (:uid, 'Onboarding charges', 'manual', 0, :charges)
    ON CONFLICT DO NOTHING
"""), {
    "uid": user_id,
    "charges": data.get("charges_mensuelles", 0)
})
