# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user

router = APIRouter(tags=["Finance"])


# =========================
# HELPERS
# =========================
def get_user_id(conn, email: str):
    row = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    return row.id if row else None


# =========================
# CREATE ITEM
# =========================
@router.post("/")
def create_finance_item(data: dict, user=Depends(get_current_user)):

    email = user

    with engine.begin() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            return {"error": "User not found"}

        conn.execute(
            text("""
                INSERT INTO finance_items (user_id, type, label, amount)
                VALUES (:user_id, :type, :label, :amount)
            """),
            {
                "user_id": user_id,
                "type": data.get("type"),
                "label": data.get("label"),
                "amount": data.get("amount", 0),
            }
        )

    return {"status": "created"}


# =========================
# GET FINANCE
# =========================
@router.get("/")
def get_finance(user=Depends(get_current_user)):

    email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            return {"error": "User not found"}

        rows = conn.execute(
            text("""
                SELECT id, type, label, amount
                FROM finance_items
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        ).fetchall()

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
# UPDATE ITEM
# =========================
@router.put("/{item_id}")
def update_finance(item_id: int, data: dict, user=Depends(get_current_user)):

    email = user

    with engine.begin() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            return {"error": "User not found"}

        conn.execute(
            text("""
                UPDATE finance_items
                SET label = :label,
                    amount = :amount
                WHERE id = :id AND user_id = :user_id
            """),
            {
                "id": item_id,
                "user_id": user_id,
                "label": data.get("label"),
                "amount": data.get("amount", 0)
            }
        )

    return {"status": "updated"}


# =========================
# DELETE ITEM
# =========================
@router.delete("/{item_id}")
def delete_finance(item_id: int, user=Depends(get_current_user)):

    email = user

    with engine.begin() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            return {"error": "User not found"}

        conn.execute(
            text("""
                DELETE FROM finance_items
                WHERE id = :id AND user_id = :user_id
            """),
            {
                "id": item_id,
                "user_id": user_id
            }
        )

    return {"status": "deleted"}

