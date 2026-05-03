# =========================
# IMPORT
# =========================

from fastapi import APIRouter

router = APIRouter()

# =========================
# POST FINANCE
# =========================
@router.post("/finance")
def create_finance_item(data: dict, user=Depends(get_current_user)):

    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO finance_items (user_id, type, label, amount)
            VALUES (:user_id, :type, :label, :amount)
        """), {
            "user_id": user.id,
            "type": data["type"],
            "label": data["label"],
            "amount": data["amount"]
        })

        conn.commit()

    return {"status": "created"}

# =========================
# GET FINANCE
# =========================
@router.get("/finance")
def get_finance(user=Depends(get_current_user)):

    with engine.connect() as conn:

        rows = conn.execute(text("""
            SELECT id, type, label, amount
            FROM finance_items
            WHERE user_id = :user_id
        """), {"user_id": user.id}).fetchall()

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
# UP DATE FINANCE
# =========================
@router.put("/finance/{item_id}")
def update_finance(item_id: int, data: dict, user=Depends(get_current_user)):

    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE finance_items
            SET label = :label,
                amount = :amount,
                updated_at = NOW()
            WHERE id = :id AND user_id = :user_id
        """), {
            "id": item_id,
            "user_id": user.id,
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

    with engine.connect() as conn:
        conn.execute(text("""
            DELETE FROM finance_items
            WHERE id = :id AND user_id = :user_id
        """), {
            "id": item_id,
            "user_id": user.id
        })

        conn.commit()

    return {"status": "deleted"}
