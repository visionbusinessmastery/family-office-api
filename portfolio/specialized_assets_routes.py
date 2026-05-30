from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from core.cache import redis_client
from database import engine
from intelligence.gamification.progress_service import award_xp
from product.asset_access import build_asset_access, enforce_asset_creation_allowed
from .specialized_assets_schemas import YieldAssetRequest, VentureAssetRequest


router = APIRouter()
_yield_schema_ready = False
_venture_schema_ready = False


def invalidate_asset_caches(email: str, user_id: int):
    try:
        if not redis_client:
            return

        redis_client.delete(
            f"yield_assets:{user_id}",
            f"venture_assets:{user_id}",
            f"cmd_center:{user_id}",
            f"intel:{email}",
            f"context:{email}",
            f"score:{email}",
            f"gamification:{email}",
        )
    except Exception:
        pass


def ensure_yield_table(conn):
    global _yield_schema_ready

    if _yield_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS yield_assets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL,
            name TEXT NOT NULL,
            principal DOUBLE PRECISION DEFAULT 0,
            average_rate DOUBLE PRECISION DEFAULT 0,
            duration_months INTEGER DEFAULT 12,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    _yield_schema_ready = True


def ensure_venture_table(conn):
    global _venture_schema_ready

    if _venture_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS venture_assets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL,
            name TEXT NOT NULL,
            revenue DOUBLE PRECISION DEFAULT 0,
            charges DOUBLE PRECISION DEFAULT 0,
            fundraising DOUBLE PRECISION DEFAULT 0,
            debts DOUBLE PRECISION DEFAULT 0,
            valuation DOUBLE PRECISION DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    _venture_schema_ready = True


def require_user_id(conn, email: str):
    if not email or email == "anonymous":
        raise HTTPException(status_code=401, detail="Session invalide")

    user_id = get_user_id(conn, email)

    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    return user_id


def build_yield_asset(row):
    principal = float(row.principal or 0)
    average_rate = float(row.average_rate or 0)
    duration_months = int(row.duration_months or 12)
    projected_gain = principal * (average_rate / 100) * (duration_months / 12)
    final_value = principal + projected_gain

    return {
        "id": row.id,
        "asset_type": row.asset_type,
        "name": row.name,
        "principal": round(principal, 2),
        "average_rate": round(average_rate, 2),
        "duration_months": duration_months,
        "projected_gain": round(projected_gain, 2),
        "final_value": round(final_value, 2),
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def build_yield_response(rows):
    assets = [build_yield_asset(row) for row in rows]
    total_principal = sum(asset["principal"] for asset in assets)
    total_gain = sum(asset["projected_gain"] for asset in assets)
    weighted_rate = (
        sum(asset["principal"] * asset["average_rate"] for asset in assets)
        / total_principal
        if total_principal > 0
        else 0
    )

    return {
        "assets": assets,
        "totals": {
            "total_principal": round(total_principal, 2),
            "total_projected_gain": round(total_gain, 2),
            "total_final_value": round(total_principal + total_gain, 2),
            "average_rate": round(weighted_rate, 2),
        },
    }


def build_venture_asset(row):
    revenue = float(row.revenue or 0)
    charges = float(row.charges or 0)
    fundraising = float(row.fundraising or 0)
    debts = float(row.debts or 0)
    valuation = float(row.valuation or 0)
    result = revenue - charges
    computed_value = max(result, 0) + fundraising - debts
    final_value = valuation if valuation > 0 else max(computed_value, 0)

    return {
        "id": row.id,
        "asset_type": row.asset_type,
        "name": row.name,
        "revenue": round(revenue, 2),
        "charges": round(charges, 2),
        "result": round(result, 2),
        "fundraising": round(fundraising, 2),
        "debts": round(debts, 2),
        "valuation": round(valuation, 2),
        "computed_value": round(computed_value, 2),
        "final_value": round(final_value, 2),
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def build_venture_response(rows, access=None):
    assets = [build_venture_asset(row) for row in rows]
    total_revenue = sum(asset["revenue"] for asset in assets)
    total_charges = sum(asset["charges"] for asset in assets)
    total_result = sum(asset["result"] for asset in assets)
    total_final_value = sum(asset["final_value"] for asset in assets)

    return {
        "assets": assets,
        "access": access,
        "totals": {
            "total_revenue": round(total_revenue, 2),
            "total_charges": round(total_charges, 2),
            "total_result": round(total_result, 2),
            "total_fundraising": round(sum(asset["fundraising"] for asset in assets), 2),
            "total_debts": round(sum(asset["debts"] for asset in assets), 2),
            "total_final_value": round(total_final_value, 2),
        },
    }


@router.get("/yield-assets/")
@router.get("/yield-assets")
def get_yield_assets(user=Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = require_user_id(conn, user)
        ensure_yield_table(conn)
        rows = conn.execute(text("""
            SELECT *
            FROM yield_assets
            WHERE user_id = :user_id
            ORDER BY created_at DESC, id DESC
        """), {"user_id": user_id}).fetchall()

    return build_yield_response(rows)


@router.post("/yield-assets/")
@router.post("/yield-assets")
def add_yield_asset(data: YieldAssetRequest, user=Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = require_user_id(conn, user)
        ensure_yield_table(conn)
        conn.execute(text("""
            INSERT INTO yield_assets (
                user_id, asset_type, name, principal, average_rate,
                duration_months, notes, updated_at
            )
            VALUES (
                :user_id, :asset_type, :name, :principal, :average_rate,
                :duration_months, :notes, NOW()
            )
        """), {
            "user_id": user_id,
            "asset_type": data.asset_type,
            "name": data.name.strip(),
            "principal": data.principal,
            "average_rate": data.average_rate,
            "duration_months": data.duration_months,
            "notes": data.notes,
        })

        award_xp(conn, user_id, user, f"yield_{data.asset_type}_created", 60)
        invalidate_asset_caches(user, user_id)

    return {"status": "created"}


@router.put("/yield-assets/{asset_id}")
def update_yield_asset(
    asset_id: int,
    data: YieldAssetRequest,
    user=Depends(get_current_user),
):
    with engine.begin() as conn:
        user_id = require_user_id(conn, user)
        ensure_yield_table(conn)
        result = conn.execute(text("""
            UPDATE yield_assets
            SET
                asset_type = :asset_type,
                name = :name,
                principal = :principal,
                average_rate = :average_rate,
                duration_months = :duration_months,
                notes = :notes,
                updated_at = NOW()
            WHERE id = :asset_id AND user_id = :user_id
        """), {
            "asset_id": asset_id,
            "user_id": user_id,
            "asset_type": data.asset_type,
            "name": data.name.strip(),
            "principal": data.principal,
            "average_rate": data.average_rate,
            "duration_months": data.duration_months,
            "notes": data.notes,
        })

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")

        award_xp(conn, user_id, user, f"yield_{data.asset_type}_updated", 15)
        invalidate_asset_caches(user, user_id)

    return {"status": "updated", "id": asset_id}


@router.delete("/yield-assets/{asset_id}")
def delete_yield_asset(asset_id: int, user=Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = require_user_id(conn, user)
        ensure_yield_table(conn)
        result = conn.execute(text("""
            DELETE FROM yield_assets
            WHERE id = :asset_id AND user_id = :user_id
        """), {"asset_id": asset_id, "user_id": user_id})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")

        invalidate_asset_caches(user, user_id)

    return {"status": "deleted", "id": asset_id}


@router.get("/venture-assets/")
@router.get("/venture-assets")
def get_venture_assets(user=Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = require_user_id(conn, user)
        ensure_venture_table(conn)
        rows = conn.execute(text("""
            SELECT *
            FROM venture_assets
            WHERE user_id = :user_id
            ORDER BY created_at DESC, id DESC
        """), {"user_id": user_id}).fetchall()
        access = build_asset_access(conn, user_id, "business", "venture_assets")

    return build_venture_response(rows, access)


@router.post("/venture-assets/")
@router.post("/venture-assets")
def add_venture_asset(data: VentureAssetRequest, user=Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = require_user_id(conn, user)
        ensure_venture_table(conn)
        enforce_asset_creation_allowed(conn, user_id, "business", "venture_assets")
        conn.execute(text("""
            INSERT INTO venture_assets (
                user_id, asset_type, name, revenue, charges, fundraising,
                debts, valuation, notes, updated_at
            )
            VALUES (
                :user_id, :asset_type, :name, :revenue, :charges, :fundraising,
                :debts, :valuation, :notes, NOW()
            )
        """), {
            "user_id": user_id,
            "asset_type": data.asset_type,
            "name": data.name.strip(),
            "revenue": data.revenue,
            "charges": data.charges,
            "fundraising": data.fundraising,
            "debts": data.debts,
            "valuation": data.valuation,
            "notes": data.notes,
        })

        award_xp(conn, user_id, user, f"venture_{data.asset_type}_created", 70)
        invalidate_asset_caches(user, user_id)

    return {"status": "created"}


@router.put("/venture-assets/{asset_id}")
def update_venture_asset(
    asset_id: int,
    data: VentureAssetRequest,
    user=Depends(get_current_user),
):
    with engine.begin() as conn:
        user_id = require_user_id(conn, user)
        ensure_venture_table(conn)
        result = conn.execute(text("""
            UPDATE venture_assets
            SET
                asset_type = :asset_type,
                name = :name,
                revenue = :revenue,
                charges = :charges,
                fundraising = :fundraising,
                debts = :debts,
                valuation = :valuation,
                notes = :notes,
                updated_at = NOW()
            WHERE id = :asset_id AND user_id = :user_id
        """), {
            "asset_id": asset_id,
            "user_id": user_id,
            "asset_type": data.asset_type,
            "name": data.name.strip(),
            "revenue": data.revenue,
            "charges": data.charges,
            "fundraising": data.fundraising,
            "debts": data.debts,
            "valuation": data.valuation,
            "notes": data.notes,
        })

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")

        award_xp(conn, user_id, user, f"venture_{data.asset_type}_updated", 20)
        invalidate_asset_caches(user, user_id)

    return {"status": "updated", "id": asset_id}


@router.delete("/venture-assets/{asset_id}")
def delete_venture_asset(asset_id: int, user=Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = require_user_id(conn, user)
        ensure_venture_table(conn)
        result = conn.execute(text("""
            DELETE FROM venture_assets
            WHERE id = :asset_id AND user_id = :user_id
        """), {"asset_id": asset_id, "user_id": user_id})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")

        invalidate_asset_caches(user, user_id)

    return {"status": "deleted", "id": asset_id}
