# =========================
# GAMIFICATION API DASHBOARD
# =========================

# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user
import json
import hashlib
from datetime import datetime

from core.cache import redis_client
from intelligence.gamification.progress_service import ensure_gamification_tables
from product.entitlements import plan_allows, resolve_effective_plan

router = APIRouter()
GAMIFICATION_STATE_VERSION = "gamification-v1"
XP_TO_NEXT_LEVEL = 1000


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


def stamp_state(payload: dict) -> dict:
    xp = int(payload.get("xp") or 0)
    payload = {
        **payload,
        "xp_to_next_level": payload.get("xp_to_next_level", XP_TO_NEXT_LEVEL),
        "progress_xp": payload.get("progress_xp", xp % XP_TO_NEXT_LEVEL),
        "progress_percent": payload.get(
            "progress_percent",
            min(100, ((xp % XP_TO_NEXT_LEVEL) / XP_TO_NEXT_LEVEL) * 100),
        ),
    }
    stamped = {
        **payload,
        "version": GAMIFICATION_STATE_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }
    stamped.pop("data_hash", None)
    stamped["data_hash"] = hashlib.sha256(
        json.dumps(stamped, sort_keys=True, default=str).encode()
    ).hexdigest()
    return stamped


def build_affiliations(conn, user_id: int):
    return []


def build_gamification_actions(score: float, level):
    return [
        {
            "title": "Mettre a jour le cockpit",
            "description": "Completer une donnee manquante ou confirmer une information existante.",
            "xp": 80,
        },
        {
            "title": "Verifier une mission",
            "description": "Ouvrir une mission en attente et verifier si sa condition backend est remplie.",
            "xp": 60,
        },
    ]


def build_upgrade(score: float, level, plan: str = "FREE"):
    if plan_allows(plan, "LEGACY"):
        return {
            "recommended_plan": "legacy",
            "title": "Legacy - Dynasty Office",
            "description": "Plan actuel actif.",
        }

    if plan_allows(plan, "LIBERTY"):
        return {
            "recommended_plan": "legacy",
            "title": "Legacy - Dynasty Office",
            "description": "Palier produit disponible au-dessus du plan actuel.",
        }

    if plan_allows(plan, "ELITE"):
        return {
            "recommended_plan": "liberty",
            "title": "Liberty - Financial Freedom",
            "description": "Palier produit disponible au-dessus du plan actuel.",
        }

    if plan_allows(plan, "GOLD"):
        return {
            "recommended_plan": "elite",
            "title": "Passer au plan Elite - Wealth OS",
            "description": "Palier produit disponible au-dessus du plan actuel.",
        }

    return {
        "recommended_plan": "gold",
        "title": "Debloquer Gold - Growth",
        "description": "Acceder au portefeuille avance, immobilier, analytics et signaux enrichis.",
    }


# =========================
# GET USER ID
# =========================
def get_user_identity(conn, email: str):
    row = conn.execute(
        text("""
            SELECT
                users.id,
                users.plan AS user_plan,
                subscriptions.plan AS subscription_plan,
                subscriptions.status AS subscription_status
            FROM users
            LEFT JOIN subscriptions ON subscriptions.user_id = users.id
            WHERE users.email = :email
        """),
        {"email": email}
    ).fetchone()

    if not row:
        return None

    return {
        "id": row.id,
        "plan": resolve_effective_plan(
            row.user_plan,
            row.subscription_plan,
            row.subscription_status,
        ),
    }


# =========================
# READ ONLY GAMIFICATION API (CACHE OPTIMIZED)
# =========================
@router.get("")
@router.get("/")
@router.get("/gamification")
def get_gamification(user=Depends(get_current_user)):

    email = user.get("email") if isinstance(user, dict) else user

    with engine.begin() as conn:

        identity = get_user_identity(conn, email)
        user_id = identity["id"] if identity else None
        plan = identity["plan"] if identity else "FREE"
        cache_key = f"gamification:{email}:{plan}"

        cached = get_cache(cache_key)
        if cached:
            return cached

        # =========================
        # FALLBACK SAFE RESPONSE
        # =========================
        default_response = {
            "xp": 0,
            "level": 1,
            "streak": 0,
            "badges": [],
            "actions": build_gamification_actions(0, "FREE"),
            "upgrade": build_upgrade(0, "FREE", plan),
            "ai_coach": {
                "message": "Progression initialisee. Les missions affichent uniquement l'avancement produit.",
                "affiliations": [],
            },
        }
        default_response = stamp_state(default_response)

        if not user_id:
            set_cache(cache_key, default_response, ttl=60)
            return default_response

        ensure_gamification_tables(conn)

        row = conn.execute(
            text("""
                SELECT xp, level, streak, badges
                FROM user_gamification
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        ).fetchone()

        if not row:
            default_response["ai_coach"]["affiliations"] = build_affiliations(conn, user_id)
            default_response = stamp_state(default_response)
            set_cache(cache_key, default_response, ttl=60)
            return default_response

        # =========================
        # SAFE BADGES PARSING
        # =========================
        badges = []

        try:
            if row.badges:
                # support JSON OR CSV
                if isinstance(row.badges, str):
                    if row.badges.startswith("["):
                        badges = json.loads(row.badges)
                    else:
                        badges = [b.strip() for b in row.badges.split(",") if b.strip()]
        except:
            badges = []

        result = {
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": row.streak or 0,
            "badges": badges,
            "actions": build_gamification_actions(row.xp or 0, row.level or 1),
            "upgrade": build_upgrade(row.xp or 0, row.level or 1, plan),
            "ai_coach": {
                "message": "Progression synchronisee. Cette zone suit XP, badges et missions uniquement.",
                "affiliations": build_affiliations(conn, user_id),
            }
        }
        result = stamp_state(result)

        # =========================
        # CACHE STORE
        # =========================
        set_cache(cache_key, result, ttl=300)

        return result
