from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from legacy.legacy_engine import compute_legacy_engine


router = APIRouter()
_legacy_schema_ready = False


class LegacyVaultRequest(BaseModel):
    title: str
    category: str | None = "private_note"
    notes: str | None = None
    confidentiality_level: str | None = "private"


class LegacyHeirRequest(BaseModel):
    name: str
    relationship: str | None = None
    age: int | None = None
    education_stage: str | None = None
    readiness_score: int | None = 0


class LegacyGovernanceRequest(BaseModel):
    title: str
    rule_type: str | None = "family_governance"
    description: str | None = None
    status: str | None = "draft"


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


def build_legacy_reading(vault_count: int, heirs_count: int, rules_count: int, scores: dict):
    weak_points = []

    if vault_count < 3:
        weak_points.append("Documents essentiels incomplets")
    if heirs_count == 0:
        weak_points.append("Aucun heritier ou beneficiaire prioritaire renseigne")
    if rules_count == 0:
        weak_points.append("Aucune regle de gouvernance formalisee")

    legacy_score = int(scores.get("legacy_score") or 0)
    if legacy_score >= 75:
        maturity = "Structuree"
    elif legacy_score >= 45:
        maturity = "En construction"
    else:
        maturity = "A structurer"

    if vault_count < 3:
        next_action = "Centraliser les 3 documents les plus importants dans le Vault."
        impact = "Renforce la protection et la continuite en cas d'urgence."
    elif heirs_count == 0:
        next_action = "Designer au moins un beneficiaire ou heritier prioritaire."
        impact = "Relie le patrimoine a une intention de transmission concrete."
    elif rules_count == 0:
        next_action = "Ajouter une premiere regle de gouvernance familiale."
        impact = "Clarifie les decisions importantes avant les moments sensibles."
    else:
        next_action = "Relire les informations Dynasty une fois par trimestre."
        impact = "Maintient la transmission vivante et exploitable."

    return {
        "maturity": maturity,
        "weak_points": weak_points[:3],
        "next_action": next_action,
        "impact": impact,
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
        vault_rows = conn.execute(text("""
            SELECT id, title, category, confidentiality_level, created_at
            FROM legacy_family_vault
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 5
        """), {"user_id": user_id}).fetchall()
        heir_rows = conn.execute(text("""
            SELECT id, name, relationship, age, education_stage, readiness_score, created_at
            FROM legacy_heirs
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 5
        """), {"user_id": user_id}).fetchall()
        rule_rows = conn.execute(text("""
            SELECT id, title, rule_type, status, created_at
            FROM legacy_governance_rules
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 5
        """), {"user_id": user_id}).fetchall()

        scores = compute_legacy_scores(vault_count, heirs_count, rules_count)
        reading = build_legacy_reading(vault_count, heirs_count, rules_count, scores)

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
        "reading": reading,
        "vault_items": [
            {
                "id": int(row.id),
                "title": row.title,
                "category": row.category,
                "confidentiality_level": row.confidentiality_level,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in vault_rows
        ],
        "heirs": [
            {
                "id": int(row.id),
                "name": row.name,
                "relationship": row.relationship,
                "age": row.age,
                "education_stage": row.education_stage,
                "readiness_score": int(row.readiness_score or 0),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in heir_rows
        ],
        "governance_rules": [
            {
                "id": int(row.id),
                "title": row.title,
                "rule_type": row.rule_type,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rule_rows
        ],
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


@router.post("/vault")
def create_vault_item(payload: LegacyVaultRequest, email: str = Depends(get_current_user)):
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Titre requis")

    with engine.begin() as conn:
        ensure_legacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        conn.execute(text("""
            INSERT INTO legacy_family_vault (
                user_id, title, category, notes, confidentiality_level, updated_at
            )
            VALUES (
                :user_id, :title, :category, :notes, :confidentiality_level, NOW()
            )
        """), {
            "user_id": user_id,
            "title": payload.title.strip(),
            "category": payload.category or "private_note",
            "notes": payload.notes,
            "confidentiality_level": payload.confidentiality_level or "private",
        })

    return {"message": "Element Vault ajoute"}


@router.post("/heirs")
def create_heir(payload: LegacyHeirRequest, email: str = Depends(get_current_user)):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Nom requis")

    with engine.begin() as conn:
        ensure_legacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        conn.execute(text("""
            INSERT INTO legacy_heirs (
                user_id, name, relationship, age, education_stage, readiness_score, updated_at
            )
            VALUES (
                :user_id, :name, :relationship, :age, :education_stage, :readiness_score, NOW()
            )
        """), {
            "user_id": user_id,
            "name": payload.name.strip(),
            "relationship": payload.relationship,
            "age": payload.age,
            "education_stage": payload.education_stage,
            "readiness_score": max(0, min(100, int(payload.readiness_score or 0))),
        })

    return {"message": "Heritier ajoute"}


@router.post("/governance-rules")
def create_governance_rule(payload: LegacyGovernanceRequest, email: str = Depends(get_current_user)):
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Titre requis")

    with engine.begin() as conn:
        ensure_legacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        conn.execute(text("""
            INSERT INTO legacy_governance_rules (
                user_id, title, rule_type, description, status, updated_at
            )
            VALUES (
                :user_id, :title, :rule_type, :description, :status, NOW()
            )
        """), {
            "user_id": user_id,
            "title": payload.title.strip(),
            "rule_type": payload.rule_type or "family_governance",
            "description": payload.description,
            "status": payload.status or "draft",
        })

    return {"message": "Regle de gouvernance ajoutee"}


@router.delete("/vault/{item_id}")
def delete_vault_item(item_id: int, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_legacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        result = conn.execute(text("""
            DELETE FROM legacy_family_vault
            WHERE id = :item_id AND user_id = :user_id
        """), {"item_id": item_id, "user_id": user_id})

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Element Vault introuvable")

    return {"message": "Element Vault supprime"}


@router.delete("/heirs/{item_id}")
def delete_heir(item_id: int, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_legacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        result = conn.execute(text("""
            DELETE FROM legacy_heirs
            WHERE id = :item_id AND user_id = :user_id
        """), {"item_id": item_id, "user_id": user_id})

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Heritier introuvable")

    return {"message": "Heritier supprime"}


@router.delete("/governance-rules/{item_id}")
def delete_governance_rule(item_id: int, email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_legacy_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        result = conn.execute(text("""
            DELETE FROM legacy_governance_rules
            WHERE id = :item_id AND user_id = :user_id
        """), {"item_id": item_id, "user_id": user_id})

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Regle introuvable")

    return {"message": "Regle de gouvernance supprimee"}
