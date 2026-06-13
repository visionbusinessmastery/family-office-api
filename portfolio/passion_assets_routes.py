from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from core.cache import redis_client
from database import engine
from product.entitlements import build_entitlements
from product.tiers import is_feature_unlocked, resolve_effective_plan


router = APIRouter()
_passion_schema_ready = False

PassionAssetType = Literal[
    "art",
    "watch",
    "car",
    "wine_spirits",
    "jewelry",
    "precious_metals",
    "collectible",
    "other",
]

PASSION_ASSET_CATEGORIES = [
    {"key": "art", "label": "Art", "description": "Oeuvres, editions, sculptures et pieces avec provenance documentable."},
    {"key": "watch", "label": "Montres", "description": "Montres de collection, numero de serie, etat, assurance et transmission."},
    {"key": "car", "label": "Voitures", "description": "Vehicules de collection ou d'exception avec valeur estimee et lieu de conservation."},
    {"key": "wine_spirits", "label": "Vins & spiritueux", "description": "Caves, bouteilles rares, millesimes et stockage specialise."},
    {"key": "jewelry", "label": "Bijoux", "description": "Bijoux, pierres, pieces certifiees et actifs assurables."},
    {"key": "precious_metals", "label": "Metaux precieux", "description": "Or, argent, platine ou pieces physiques declarees."},
    {"key": "collectible", "label": "Collections", "description": "Objets rares, souvenirs historiques ou collections specialisees."},
    {"key": "other", "label": "Autres", "description": "Autres actifs tangibles a valeur patrimoniale ou familiale."},
]


class PassionAssetRequest(BaseModel):
    asset_type: PassionAssetType
    name: str = Field(min_length=1)
    acquisition_value: float = Field(default=0, ge=0)
    estimated_value: float = Field(default=0, ge=0)
    acquisition_year: Optional[int] = Field(default=None, ge=1800, le=2200)
    provenance: Optional[str] = None
    storage_location: Optional[str] = None
    insured_value: float = Field(default=0, ge=0)
    beneficiary: Optional[str] = None
    notes: Optional[str] = None


def ensure_passion_assets_table(conn):
    global _passion_schema_ready

    if _passion_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS passion_assets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            asset_type TEXT NOT NULL,
            name TEXT NOT NULL,
            acquisition_value DOUBLE PRECISION DEFAULT 0,
            estimated_value DOUBLE PRECISION DEFAULT 0,
            acquisition_year INTEGER,
            provenance TEXT,
            storage_location TEXT,
            insured_value DOUBLE PRECISION DEFAULT 0,
            beneficiary TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS passion_asset_categories (
            key TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    for index, category in enumerate(PASSION_ASSET_CATEGORIES, start=1):
        conn.execute(text("""
            INSERT INTO passion_asset_categories (key, label, description, sort_order)
            VALUES (:key, :label, :description, :sort_order)
            ON CONFLICT (key) DO UPDATE
            SET label = EXCLUDED.label,
                description = EXCLUDED.description,
                sort_order = EXCLUDED.sort_order,
                updated_at = NOW()
        """), {**category, "sort_order": index})

    _passion_schema_ready = True


def invalidate_passion_asset_caches(email: str, user_id: int):
    try:
        if redis_client:
            redis_client.delete(
                f"passion_assets:{user_id}",
                f"context:{email}",
                f"intel:{email}",
                f"score:{email}",
                f"gamification:{email}",
            )
    except Exception:
        pass


def require_user_id(conn, email: str):
    if not email or email == "anonymous":
        raise HTTPException(status_code=401, detail="Session invalide")

    user_id = get_user_id(conn, email)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    return user_id


def current_user_email(user):
    if isinstance(user, str):
        return user
    if isinstance(user, dict):
        return user.get("email")
    return None


def get_passion_access(conn, user_id: int):
    row = conn.execute(text("""
        SELECT
            users.plan AS user_plan,
            subscriptions.plan AS subscription_plan,
            subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.id = :user_id
    """), {"user_id": user_id}).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    plan = resolve_effective_plan(row.user_plan, row.subscription_plan, row.subscription_status)
    entitlements = build_entitlements(plan)
    return {
        "plan": plan,
        "available": is_feature_unlocked(plan, "alternative_assets"),
        "required_plan": "LIBERTY",
        "feature": "alternative_assets",
        "copy": next(
            (
                feature
                for feature in entitlements.get("feature_access", [])
                if feature.get("key") == "alternative_assets"
            ),
            None,
        ),
    }


def build_asset(row):
    acquisition_value = float(row.acquisition_value or 0)
    estimated_value = float(row.estimated_value or 0)
    latent_gain = estimated_value - acquisition_value
    performance = (latent_gain / acquisition_value * 100) if acquisition_value > 0 else 0

    return {
        "id": int(row.id),
        "asset_type": row.asset_type,
        "name": row.name,
        "acquisition_value": round(acquisition_value, 2),
        "estimated_value": round(estimated_value, 2),
        "latent_gain": round(latent_gain, 2),
        "performance": round(performance, 2),
        "acquisition_year": row.acquisition_year,
        "provenance": row.provenance,
        "storage_location": row.storage_location,
        "insured_value": round(float(row.insured_value or 0), 2),
        "beneficiary": row.beneficiary,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def build_response(rows, access):
    assets = [build_asset(row) for row in rows]
    total_acquisition = sum(asset["acquisition_value"] for asset in assets)
    total_estimated = sum(asset["estimated_value"] for asset in assets)
    total_gain = total_estimated - total_acquisition
    dominant = None
    if assets and total_estimated > 0:
        by_type = {}
        for asset in assets:
            by_type[asset["asset_type"]] = by_type.get(asset["asset_type"], 0) + asset["estimated_value"]
        dominant_key, dominant_value = max(by_type.items(), key=lambda item: item[1])
        dominant = {
            "asset_type": dominant_key,
            "value": round(dominant_value, 2),
            "percent": round((dominant_value / total_estimated) * 100, 1),
        }

    return {
        "access": access,
        "assets": assets,
        "totals": {
            "count": len(assets),
            "acquisition_value": round(total_acquisition, 2),
            "estimated_value": round(total_estimated, 2),
            "latent_gain": round(total_gain, 2),
            "performance": round((total_gain / total_acquisition * 100) if total_acquisition > 0 else 0, 2),
            "insured_value": round(sum(asset["insured_value"] for asset in assets), 2),
            "dominant": dominant,
        },
    }


@router.get("/passion-assets/")
@router.get("/passion-assets")
def list_passion_assets(user=Depends(get_current_user)):
    email = current_user_email(user)
    with engine.begin() as conn:
        ensure_passion_assets_table(conn)
        user_id = require_user_id(conn, email)
        access = get_passion_access(conn, user_id)
        rows = conn.execute(text("""
            SELECT *
            FROM passion_assets
            WHERE user_id = :user_id
            ORDER BY estimated_value DESC, created_at DESC
        """), {"user_id": user_id}).fetchall()

    return build_response(rows, access)


@router.get("/passion-assets/catalog")
def passion_assets_catalog(user=Depends(get_current_user)):
    email = current_user_email(user)
    with engine.begin() as conn:
        ensure_passion_assets_table(conn)
        user_id = require_user_id(conn, email)
        access = get_passion_access(conn, user_id)

        categories = conn.execute(text("""
            SELECT key, label, description
            FROM passion_asset_categories
            ORDER BY sort_order ASC, label ASC
        """)).fetchall()

    return {
        "access": access,
        "categories": [
            {"key": row.key, "label": row.label, "description": row.description}
            for row in categories
        ],
        "fields": [
            "asset_type",
            "name",
            "acquisition_value",
            "estimated_value",
            "acquisition_year",
            "provenance",
            "storage_location",
            "insured_value",
            "beneficiary",
            "notes",
        ],
    }


@router.post("/passion-assets/")
@router.post("/passion-assets")
def create_passion_asset(payload: PassionAssetRequest, user=Depends(get_current_user)):
    email = current_user_email(user)
    with engine.begin() as conn:
        ensure_passion_assets_table(conn)
        user_id = require_user_id(conn, email)
        access = get_passion_access(conn, user_id)
        if not access.get("available"):
            raise HTTPException(status_code=403, detail="Passion Assets est disponible a partir du plan Liberty.")

        conn.execute(text("""
            INSERT INTO passion_assets (
                user_id, asset_type, name, acquisition_value, estimated_value,
                acquisition_year, provenance, storage_location, insured_value,
                beneficiary, notes
            )
            VALUES (
                :user_id, :asset_type, :name, :acquisition_value, :estimated_value,
                :acquisition_year, :provenance, :storage_location, :insured_value,
                :beneficiary, :notes
            )
        """), {"user_id": user_id, **payload.dict()})

        invalidate_passion_asset_caches(email, user_id)
        rows = conn.execute(text("""
            SELECT *
            FROM passion_assets
            WHERE user_id = :user_id
            ORDER BY estimated_value DESC, created_at DESC
        """), {"user_id": user_id}).fetchall()

    return build_response(rows, access)


@router.put("/passion-assets/{asset_id}")
def update_passion_asset(asset_id: int, payload: PassionAssetRequest, user=Depends(get_current_user)):
    email = current_user_email(user)
    with engine.begin() as conn:
        ensure_passion_assets_table(conn)
        user_id = require_user_id(conn, email)
        access = get_passion_access(conn, user_id)
        if not access.get("available"):
            raise HTTPException(status_code=403, detail="Passion Assets est disponible a partir du plan Liberty.")

        result = conn.execute(text("""
            UPDATE passion_assets
            SET asset_type = :asset_type,
                name = :name,
                acquisition_value = :acquisition_value,
                estimated_value = :estimated_value,
                acquisition_year = :acquisition_year,
                provenance = :provenance,
                storage_location = :storage_location,
                insured_value = :insured_value,
                beneficiary = :beneficiary,
                notes = :notes,
                updated_at = NOW()
            WHERE id = :asset_id AND user_id = :user_id
        """), {"asset_id": asset_id, "user_id": user_id, **payload.dict()})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Passion asset not found")

        invalidate_passion_asset_caches(email, user_id)
        rows = conn.execute(text("""
            SELECT *
            FROM passion_assets
            WHERE user_id = :user_id
            ORDER BY estimated_value DESC, created_at DESC
        """), {"user_id": user_id}).fetchall()

    return build_response(rows, access)


@router.delete("/passion-assets/{asset_id}")
def delete_passion_asset(asset_id: int, user=Depends(get_current_user)):
    email = current_user_email(user)
    with engine.begin() as conn:
        ensure_passion_assets_table(conn)
        user_id = require_user_id(conn, email)
        access = get_passion_access(conn, user_id)

        result = conn.execute(text("""
            DELETE FROM passion_assets
            WHERE id = :asset_id AND user_id = :user_id
        """), {"asset_id": asset_id, "user_id": user_id})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Passion asset not found")

        invalidate_passion_asset_caches(email, user_id)
        rows = conn.execute(text("""
            SELECT *
            FROM passion_assets
            WHERE user_id = :user_id
            ORDER BY estimated_value DESC, created_at DESC
        """), {"user_id": user_id}).fetchall()

    return build_response(rows, access)
