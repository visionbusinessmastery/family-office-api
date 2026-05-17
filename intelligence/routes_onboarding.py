# =========================
# INTELLIGENCE ROUTES ONBOARDING
# =========================

# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user
from core.cache import redis_client

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# =========================
# INVALIDATE USER INTELLIGENCE CACHE
# =========================
def invalidate_user_intelligence_caches(email: str):
    try:
        if redis_client:
            redis_client.delete(
                f"intel:{email}",
                f"context:{email}",
                f"score:{email}",
            )
    except Exception:
        pass


# =========================
# ONBOARDING UPDATE (IDEMPOTENT & SAFE)
# =========================
@router.put("/")
def update_onboarding(data: dict, user=Depends(get_current_user)):

    # =========================
    # SAFE EMAIL EXTRACTION
    # =========================
    email = user.get("email") if isinstance(user, dict) else user
    
    # =========================
    # SAFE CASTING
    # =========================
    revenus = float(data.get("revenus_mensuels") or 0)
    charges = float(data.get("charges_mensuelles") or 0)

    try:
        with engine.begin() as conn:

            # =========================
            # UPDATE USER SNAPSHOT (base pour photo utilisateur)
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
                return {"status": "error", "message": "User not found"}

            # =========================
            # GET USER ID (pour tables financières)
            # =========================
            user_id_row = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": email}).fetchone()

            if not user_id_row:
                return {"status": "error", "message": "User ID not found"}

            uid = user_id_row.id

            # =========================
            # SYNC → INCOME SOURCES (IDEMPOTENT)
            # =========================
            conn.execute(text("""
                DELETE FROM income_sources
                WHERE user_id = :uid AND income_type = 'onboarding'
            """), {"uid": uid})

            conn.execute(text("""
                INSERT INTO income_sources (user_id, name, income_type, monthly_income)
                VALUES (:uid, 'Onboarding Income', 'onboarding', :income)
            """), {
                "uid": uid,
                "income": revenus
            })

            # =========================
            # SYNC → DEBTS (IDEMPOTENT)
            # =========================
            conn.execute(text("""
                DELETE FROM debts
                WHERE user_id = :uid AND debt_type = 'onboarding'
            """), {"uid": uid})

            conn.execute(text("""
                INSERT INTO debts (user_id, name, debt_type, remaining_amount, monthly_payment)
                VALUES (:uid, 'Onboarding Charges', 'onboarding', 0, :charges)
            """), {
                "uid": uid,
                "charges": charges
            })
            
        invalidate_user_intelligence_caches(email)

    
        # =========================
        # SUCCESS RESPONSE
        # =========================
        return {
            "status": "success",
            "message": "Onboarding saved & synced"
        }

    except Exception as e:
        # =========================
        # ERROR HANDLING
        # =========================
        return {
            "status": "error",
            "detail": str(e)
        }
