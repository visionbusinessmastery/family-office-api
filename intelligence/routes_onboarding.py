from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user

router = APIRouter()

def get_user_id(conn, email):
    user = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()
    return user.id if user else None


@router.put("/onboarding")
def update_onboarding(data: dict, user=Depends(get_current_user)):

    with engine.begin() as conn:
        user_id = get_user_id(conn, user)

        if not user_id:
            return {"error": "User not found"}

        conn.execute(text("""
            UPDATE users
            SET revenus = :revenus,
                dettes = :dettes,
                epargne = :epargne
            WHERE id = :user_id
        """), {
            "user_id": user_id,
            "revenus": data.get("revenus", 0),
            "dettes": data.get("dettes", 0),
            "epargne": data.get("epargne", 0),
        })

    return {"status": "updated"}
