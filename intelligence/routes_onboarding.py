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
