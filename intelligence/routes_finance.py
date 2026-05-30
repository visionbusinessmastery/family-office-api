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
from intelligence.gamification.progress_service import award_xp

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
            keys.append(f"financial_overview:{user_id}")

        redis_client.delete(*keys)
    except Exception:
        pass


def get_item_name(data: dict):
    return data.get("name") or data.get("label") or ""


# =========================
# CREATE ITEM
# =========================
@router.post("")
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

        award_xp(conn, user_id, email, f"finance_{data.get('type')}_created", 30)
        invalidate_finance_caches(email, user_id)
  
    return {"status": "created"}


# =========================
# GET FINANCE
# =========================
@router.get("")
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


@router.get("/overview")
def get_finance_overview(user=Depends(get_current_user)):

    email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            return {"error": "User not found"}

        rows = conn.execute(
            text("""
                SELECT type, COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
                FROM finance_items
                WHERE user_id = :user_id
                GROUP BY type
            """),
            {"user_id": user_id}
        ).fetchall()

    totals = {
        "revenus": 0.0,
        "charges": 0.0,
        "epargne": 0.0,
        "dettes": 0.0,
    }
    counts = {
        "revenus": 0,
        "charges": 0,
        "epargne": 0,
        "dettes": 0,
    }

    for row in rows:
        if row.type in totals:
            totals[row.type] = float(row.total or 0)
            counts[row.type] = int(row.count or 0)

    income = totals["revenus"]
    expenses = totals["charges"]
    savings = totals["epargne"]
    debt = totals["dettes"]
    cashflow = income - expenses
    savings_rate = (cashflow / income * 100) if income > 0 else 0
    debt_to_income = (debt / income) if income > 0 else 0
    liquid_months = (savings / expenses) if expenses > 0 else 0

    if income <= 0:
        reading = "Ajoute tes revenus suivis pour obtenir une lecture fiable de ta marge de liberte mensuelle."
        priority = "Renseigner les revenus recurrents"
    elif cashflow > 0:
        reading = "Ta base financiere montre une marge mensuelle positive a partir des lignes deja renseignees."
        priority = "Transformer cette marge en coussin de securite et trajectoire d'epargne."
    else:
        reading = "Les charges suivies absorbent les revenus renseignes. La priorite est de retrouver une marge positive."
        priority = "Identifier une charge ajustable ou un revenu complementaire."

    return {
        "version": "finance-overview-v1",
        "source": "finance_items",
        "totals": {
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "cashflow": round(cashflow, 2),
            "living_margin": round(cashflow, 2),
            "savings": round(savings, 2),
            "debt": round(debt, 2),
        },
        "ratios": {
            "savings_rate": round(savings_rate, 2),
            "debt_to_income": round(debt_to_income, 2),
            "liquid_months": round(liquid_months, 2),
        },
        "counts": counts,
        "reading": reading,
        "priority": priority,
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

        award_xp(conn, user_id, email, "finance_updated", 10)
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
