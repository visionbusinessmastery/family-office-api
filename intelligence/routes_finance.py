# =========================
# IMPORT
# =========================
from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user 

router = APIRouter()

# =========================
# HELPER
# =========================
def get_user_id(conn, email):
    user_row = conn.execute(text("""
        SELECT id FROM users WHERE email = :email
    """), {"email": email}).fetchone()

    return user_row.id if user_row else None


# =========================
# POST FINANCE
# =========================
@router.post("/finance")
def create_finance_item(data: dict, user=Depends(get_current_user)):

    user_email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, user_email)

        if not user_id:
            return {"error": "User not found"}

        conn.execute(text("""
            INSERT INTO finance_items (user_id, type, label, amount)
            VALUES (:user_id, :type, :label, :amount)
        """), {
            "user_id": user_id,
            type_ = data.get("type")
            label = data.get("label")
            amount = data.get("amount")

           if not type_ or not label or amount is None:
               return {"error": "missing fields"}
        })

        conn.commit()

    return {"status": "created"}


# =========================
# GET FINANCE
# =========================
@router.get("/finance")
def get_finance(user=Depends(get_current_user)):

    user_email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, user_email)

        if not user_id:
            return {"error": "User not found"}

        rows = conn.execute(text("""
            SELECT id, type, label, amount
            FROM finance_items
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()

    revenues = []
    debts = []
    savings = []

    for r in rows:
        item = {
            "id": r.id,
            "label": r.label,
            "amount": float(r.amount or 0)
        }

        if r.type == "revenus":
            revenues.append(item)
        elif r.type == "dettes":
            debts.append(item)
        elif r.type == "epargne":
            savings.append(item)

    return {
        "revenus": revenues,
        "dettes": debts,
        "epargne": savings
    }


# =========================
# UPDATE FINANCE
# =========================
@router.put("/finance/{item_id}")
def update_finance(item_id: int, data: dict, user=Depends(get_current_user)):

    user_email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, user_email)

        if not user_id:
            return {"error": "User not found"}

        conn.execute(text("""
            UPDATE finance_items
            SET label = :label,
                amount = :amount
            WHERE id = :id AND user_id = :user_id
        """), {
            "id": item_id,
            "user_id": user_id,
            "label": data["label"],
            "amount": data["amount"]
        })

        conn.commit()

    return {"status": "updated"}


# =========================
# DELETE FINANCE
# =========================
@router.delete("/finance/{item_id}")
def delete_finance(item_id: int, user=Depends(get_current_user)):

    user_email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, user_email)

        if not user_id:
            return {"error": "User not found"}

        conn.execute(text("""
            DELETE FROM finance_items
            WHERE id = :id AND user_id = :user_id
        """), {
            "id": item_id,
            "user_id": user_id
        })

        conn.commit()

    return {"status": "deleted"}
