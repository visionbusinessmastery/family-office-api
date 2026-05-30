from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from core.cache import redis_client
from database import engine
from intelligence.gamification.progress_service import award_xp
from product.asset_access import build_asset_access, enforce_asset_creation_allowed
from .real_estate_schemas import RealEstateRequest


router = APIRouter()
_real_estate_schema_ready = False


def ensure_real_estate_table(conn):
    global _real_estate_schema_ready

    if _real_estate_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS real_estate_assets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            property_type TEXT NOT NULL,
            name TEXT NOT NULL,
            purchase_price DOUBLE PRECISION DEFAULT 0,
            estimated_value DOUBLE PRECISION DEFAULT 0,
            resale_price DOUBLE PRECISION DEFAULT 0,
            monthly_rent DOUBLE PRECISION DEFAULT 0,
            monthly_charges DOUBLE PRECISION DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    _real_estate_schema_ready = True


def invalidate_real_estate_caches(email: str, user_id: int):
    try:
        if not redis_client:
            return

        redis_client.delete(
            f"real_estate:{user_id}",
            f"cmd_center:{user_id}",
            f"intel:{email}",
            f"context:{email}",
            f"score:{email}",
        )
    except Exception:
        pass


def build_asset(row):
    purchase_price = float(row.purchase_price or 0)
    estimated_value = float(row.estimated_value or 0)
    resale_price = float(row.resale_price or 0)
    monthly_rent = float(row.monthly_rent or 0)
    monthly_charges = float(row.monthly_charges or 0)

    if row.property_type == "flip":
        target_value = resale_price or estimated_value or purchase_price
    else:
        target_value = estimated_value or purchase_price

    potential_gain = target_value - purchase_price
    annual_net_rent = max(monthly_rent - monthly_charges, 0) * 12
    rental_yield = (
        annual_net_rent / purchase_price * 100
        if row.property_type == "rental" and purchase_price > 0
        else 0
    )

    return {
        "id": row.id,
        "property_type": row.property_type,
        "name": row.name,
        "purchase_price": round(purchase_price, 2),
        "estimated_value": round(estimated_value, 2),
        "resale_price": round(resale_price, 2),
        "monthly_rent": round(monthly_rent, 2),
        "monthly_charges": round(monthly_charges, 2),
        "target_value": round(target_value, 2),
        "potential_gain": round(potential_gain, 2),
        "potential_gain_percent": round(
            (potential_gain / purchase_price * 100) if purchase_price > 0 else 0,
            2,
        ),
        "annual_net_rent": round(annual_net_rent, 2),
        "rental_yield": round(rental_yield, 2),
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def build_response(rows, access=None):
    assets = [build_asset(row) for row in rows]
    rental_assets = [asset for asset in assets if asset["property_type"] == "rental"]
    total_purchase = sum(asset["purchase_price"] for asset in assets)
    total_target_value = sum(asset["target_value"] for asset in assets)
    total_potential_gain = total_target_value - total_purchase
    average_rental_yield = (
        sum(asset["rental_yield"] for asset in rental_assets) / len(rental_assets)
        if rental_assets
        else 0
    )

    return {
        "assets": assets,
        "access": access,
        "totals": {
            "total_purchase": round(total_purchase, 2),
            "total_estimated_value": round(total_target_value, 2),
            "total_potential_gain": round(total_potential_gain, 2),
            "total_potential_gain_percent": round(
                (total_potential_gain / total_purchase * 100)
                if total_purchase > 0
                else 0,
                2,
            ),
            "average_rental_yield": round(average_rental_yield, 2),
        },
    }


def get_real_estate_rows(conn, user_id: int):
    ensure_real_estate_table(conn)

    return conn.execute(text("""
        SELECT
            id,
            property_type,
            name,
            purchase_price,
            estimated_value,
            resale_price,
            monthly_rent,
            monthly_charges,
            notes,
            created_at,
            updated_at
        FROM real_estate_assets
        WHERE user_id = :user_id
        ORDER BY created_at DESC, id DESC
    """), {"user_id": user_id}).fetchall()


def list_real_estate_assets(user):
    with engine.begin() as conn:
        user_id = get_user_id(conn, user)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        rows = get_real_estate_rows(conn, user_id)
        access = build_asset_access(conn, user_id, "real_estate", "real_estate_assets")

    return build_response(rows, access)


@router.get("/")
def get_real_estate(user=Depends(get_current_user)):
    return list_real_estate_assets(user)


@router.get("")
def get_real_estate_no_slash(user=Depends(get_current_user)):
    return list_real_estate_assets(user)


def create_real_estate_asset(data: RealEstateRequest, user):
    with engine.begin() as conn:
        user_id = get_user_id(conn, user)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        ensure_real_estate_table(conn)
        enforce_asset_creation_allowed(conn, user_id, "real_estate", "real_estate_assets")

        conn.execute(text("""
            INSERT INTO real_estate_assets (
                user_id,
                property_type,
                name,
                purchase_price,
                estimated_value,
                resale_price,
                monthly_rent,
                monthly_charges,
                notes,
                updated_at
            )
            VALUES (
                :user_id,
                :property_type,
                :name,
                :purchase_price,
                :estimated_value,
                :resale_price,
                :monthly_rent,
                :monthly_charges,
                :notes,
                NOW()
            )
        """), {
            "user_id": user_id,
            "property_type": data.property_type,
            "name": data.name.strip(),
            "purchase_price": data.purchase_price,
            "estimated_value": data.estimated_value,
            "resale_price": data.resale_price,
            "monthly_rent": data.monthly_rent,
            "monthly_charges": data.monthly_charges,
            "notes": data.notes,
        })

        award_xp(conn, user_id, user, "real_estate_asset_created", 80)
        invalidate_real_estate_caches(user, user_id)

    return {"status": "created"}


@router.post("/")
def add_real_estate_asset(data: RealEstateRequest, user=Depends(get_current_user)):
    return create_real_estate_asset(data, user)


@router.post("")
def add_real_estate_asset_no_slash(
    data: RealEstateRequest,
    user=Depends(get_current_user),
):
    return create_real_estate_asset(data, user)


@router.put("/{asset_id}")
def update_real_estate_asset(
    asset_id: int,
    data: RealEstateRequest,
    user=Depends(get_current_user),
):
    with engine.begin() as conn:
        user_id = get_user_id(conn, user)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        ensure_real_estate_table(conn)

        result = conn.execute(text("""
            UPDATE real_estate_assets
            SET
                property_type = :property_type,
                name = :name,
                purchase_price = :purchase_price,
                estimated_value = :estimated_value,
                resale_price = :resale_price,
                monthly_rent = :monthly_rent,
                monthly_charges = :monthly_charges,
                notes = :notes,
                updated_at = NOW()
            WHERE id = :asset_id AND user_id = :user_id
        """), {
            "asset_id": asset_id,
            "user_id": user_id,
            "property_type": data.property_type,
            "name": data.name.strip(),
            "purchase_price": data.purchase_price,
            "estimated_value": data.estimated_value,
            "resale_price": data.resale_price,
            "monthly_rent": data.monthly_rent,
            "monthly_charges": data.monthly_charges,
            "notes": data.notes,
        })

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")

        award_xp(conn, user_id, user, "real_estate_asset_updated", 20)
        invalidate_real_estate_caches(user, user_id)

    return {"status": "updated", "id": asset_id}


@router.delete("/{asset_id}")
def delete_real_estate_asset(asset_id: int, user=Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = get_user_id(conn, user)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        ensure_real_estate_table(conn)

        result = conn.execute(text("""
            DELETE FROM real_estate_assets
            WHERE id = :asset_id AND user_id = :user_id
        """), {
            "asset_id": asset_id,
            "user_id": user_id,
        })

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Asset not found")

        invalidate_real_estate_caches(user, user_id)

    return {"status": "deleted", "id": asset_id}
