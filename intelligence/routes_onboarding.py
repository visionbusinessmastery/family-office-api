# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


# =========================
# ONBOARDING UPDATE (FINAL CLEAN VERSION)
# =========================
@router.put("/")
def update_onboarding(data: dict, user=Depends(get_current_user)):

    # =========================
    # SAFE EMAIL EXTRACTION
    # =========================
    email = user.get("email") if isinstance(user, dict) else user.email

    revenus = data.get("revenus_mensuels", 0)
    charges = data.get("charges_mensuelles", 0)

    try:
        with engine.begin() as conn:

            # =========================
            # UPDATE USER PROFILE
            # =========================
            result = conn.execute(text("""
                UPDATE users
                SET revenus_mensuels = :revenus,
                    charges_mensuelles = :charges,
                    profile_completed = TRUE
                WHERE email = :email
            """), {
                "email": email,
                "revenus": revenus,
                "charges": charges,
            })

            if result.rowcount == 0:
                return {"error": "User not found"}

            # =========================
            # GET USER ID (FOR FINANCIAL TABLES)
            # =========================
            user_id = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": email}).fetchone()

            if not user_id:
                return {"error": "User ID not found"}

            uid = user_id.id

            # =========================
            # SYNC → INCOME SOURCES
            # =========================
            conn.execute(text("""
                INSERT INTO income_sources (user_id, name, income_type, monthly_income)
                VALUES (:uid, 'Onboarding Income', 'manual', :income)
            """), {
                "uid": uid,
                "income": revenus
            })

            # =========================
            # SYNC → DEBTS (charges = monthly debt proxy)
            # =========================
            conn.execute(text("""
                INSERT INTO debts (user_id, name, debt_type, remaining_amount, monthly_payment)
                VALUES (:uid, 'Onboarding Charges', 'manual', 0, :charges)
            """), {
                "uid": uid,
                "charges": charges
            })

        return {
            "status": "success",
            "message": "Onboarding saved & synced"
        }

    except Exception as e:
        return {
            "status": "error",
            "detail": str(e)
        }
