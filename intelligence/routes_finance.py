# =========================
# INTELLIGENCE ROUTES FINANCE
# =========================

# =========================
# IMPORTS
# =========================
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user
from core.cache import redis_client

router = APIRouter(tags=["Finance"])

# =========================
# HELPER
# =========================
def get_user_id(conn, email: str):
    row = conn.execute(
        text("""
            SELECT id
            FROM users
            WHERE email = :email
        """),
        {"email": email}
    ).fetchone()

    return row.id if row else None

# =========================
# INVALIDATE FINANCE CACHE
# =========================
def invalidate_finance_caches(email: str, user_id: Optional[int] = None):
    try:
        if not redis_client:
            return

        keys = [
            f"intel:{email}",
            f"context:{email}",
            f"score:{email}",
        ]

        if user_id is not None:
            keys.append(f"financial:{user_id}")

        redis_client.delete(*keys)
    except Exception:
        pass


def get_item_name(data: dict):
    return data.get("name") or data.get("label") or ""


# =========================
# CREATE ITEM
# =========================
@router.post("/")
def create_finance_item(data: dict, user=Depends(get_current_user)):

    email = user

    with engine.begin() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(
              status_code=404,
              detail="User not found"
            )
        conn.execute(
            text("""
                INSERT INTO finance_items (user_id, type, name, amount)
                VALUES (:user_id, :type, :name, :amount)
            """),
            {
                "user_id": user_id,
                "type": data.get("type"),
                "name": get_item_name(data),
                "amount": data.get("amount", 0),
            }
        )

        invalidate_finance_caches(email, user_id)
  
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
                SELECT id, type, name, amount
                FROM finance_items
                WHERE user_id = :user_id
                ORDER BY id DESC
            """),
            {"user_id": user_id}
        ).fetchall()

    revenues = []
    charges = []
    debts = []
    savings = []

    for r in rows:

        item = {
            "id": r.id,
            "type": r.type,
            "name": r.name,
            "label": r.name,
            "amount": float(r.amount or 0)
        }

        if r.type == "revenus":
            revenues.append(item)

        elif r.type == "charges":
            charges.append(item)

        elif r.type == "dettes":
            debts.append(item)

        elif r.type == "epargne":
            savings.append(item)

    return {
        "revenus": revenues,
        "charges": charges,
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
                SET name = :name,
                    amount = :amount
                WHERE id = :id AND user_id = :user_id
            """),
            {
                "id": item_id,
                "user_id": user_id,
                "name": get_item_name(data),
                "amount": data.get("amount", 0)
            }
        )

        invalidate_finance_caches(email, user_id)

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

        invalidate_finance_caches(email, user_id)
        
    return {"status": "deleted"}


# =========================
# ADD XP
# =========================
def add_xp(conn, user_id: int, xp_amount: int):

    row = conn.execute(
        text("""
            SELECT xp
            FROM user_gamification
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).fetchone()

    if not row:

        conn.execute(
            text("""
                INSERT INTO user_gamification
                (user_id, xp, level)
                VALUES (:user_id, :xp, :level)
            """),
            {
                "user_id": user_id,
                "xp": xp_amount,
                "level": 1
            }
        )

    else:

        new_xp = row.xp + xp_amount
        level = int(new_xp / 100) + 1

        conn.execute(
            text("""
                UPDATE user_gamification
                SET xp = :xp,
                    level = :level
                WHERE user_id = :user_id
            """),
            {
                "xp": new_xp,
                "level": level,
                "user_id": user_id
            }
        )
