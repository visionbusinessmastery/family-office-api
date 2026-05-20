from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from legacy.legacy_engine import compute_legacy_engine


router = APIRouter()
_legacy_schema_ready = False


def ensure_legacy_tables(conn):
    global _legacy_schema_ready

    if _legacy_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS legacy_family_vault (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT DEFAULT 'private_note',
            notes TEXT,
            confidentiality_level TEXT DEFAULT 'private',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS legacy_family_vault_user_idx
        ON legacy_family_vault(user_id)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS legacy_heirs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            relationship TEXT,
            age INTEGER,
            education_stage TEXT,
            readiness_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS legacy_heirs_user_idx
        ON legacy_heirs(user_id)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS legacy_governance_rules (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            rule_type TEXT DEFAULT 'family_governance',
            description TEXT,
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS legacy_governance_rules_user_idx
        ON legacy_governance_rules(user_id)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS legacy_metrics (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            legacy_score INTEGER DEFAULT 0,
            dynasty_stability_score INTEGER DEFAULT 0,
            transmission_readiness INTEGER DEFAULT 0,
            family_governance_index INTEGER DEFAULT 0,
            asset_protection_index INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    _legacy_schema_ready = True


def compute_legacy_scores(vault_count: int, heirs_count: int, rules_count: int):
    transmission = min(100, vault_count * 15 + heirs_count * 20)
    governance = min(100, rules_count * 25)
    protection = min(100, vault_count * 10 + rules_count * 15)
    stability = round((transmission + governance + protection) / 3)

    return {
        "legacy_score": round((transmission + governance + protection + stability) / 4),
        "dynasty_stability_score": stability,
        "transmission_readiness": transmission,
        "family_governance_index": governance,
        "asset_protection_index": protection,
    }


@router.get("/overview")
def legacy_overview(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_legacy_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        vault_count = int(conn.execute(text("""
            SELECT COUNT(*) FROM legacy_family_vault WHERE user_id = :user_id
        """), {"user_id": user_id}).scalar() or 0)
        heirs_count = int(conn.execute(text("""
            SELECT COUNT(*) FROM legacy_heirs WHERE user_id = :user_id
        """), {"user_id": user_id}).scalar() or 0)
        rules_count = int(conn.execute(text("""
            SELECT COUNT(*) FROM legacy_governance_rules WHERE user_id = :user_id
        """), {"user_id": user_id}).scalar() or 0)

        scores = compute_legacy_scores(vault_count, heirs_count, rules_count)

        conn.execute(text("""
            INSERT INTO legacy_metrics (
                user_id, legacy_score, dynasty_stability_score,
                transmission_readiness, family_governance_index,
                asset_protection_index, updated_at
            )
            VALUES (
                :user_id, :legacy_score, :dynasty_stability_score,
                :transmission_readiness, :family_governance_index,
                :asset_protection_index, NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                legacy_score = EXCLUDED.legacy_score,
                dynasty_stability_score = EXCLUDED.dynasty_stability_score,
                transmission_readiness = EXCLUDED.transmission_readiness,
                family_governance_index = EXCLUDED.family_governance_index,
                asset_protection_index = EXCLUDED.asset_protection_index,
                updated_at = NOW()
        """), {"user_id": user_id, **scores})

    return {
        "counts": {
            "family_vault": vault_count,
            "heirs": heirs_count,
            "governance_rules": rules_count,
        },
        "scores": scores,
        "insights": [
            "La richesse se construit vite. L'heritage demande plusieurs generations.",
            "Ton patrimoine doit survivre a tes emotions.",
            "La discretion protege davantage que l'exposition.",
        ],
        "modules": [
            "Family Vault",
            "Governance",
            "Heirs",
            "Protection Layer",
            "Global Strategy",
            "Legacy Timeline",
        ],
    }


@router.get("/engine")
def legacy_engine(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_legacy_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        vault_count = int(conn.execute(text("""
            SELECT COUNT(*) FROM legacy_family_vault WHERE user_id = :user_id
        """), {"user_id": user_id}).scalar() or 0)
        heirs_count = int(conn.execute(text("""
            SELECT COUNT(*) FROM legacy_heirs WHERE user_id = :user_id
        """), {"user_id": user_id}).scalar() or 0)
        rules_count = int(conn.execute(text("""
            SELECT COUNT(*) FROM legacy_governance_rules WHERE user_id = :user_id
        """), {"user_id": user_id}).scalar() or 0)

    return compute_legacy_engine({
        "vault_count": vault_count,
        "heirs_count": heirs_count,
        "governance_rules": rules_count,
    })
