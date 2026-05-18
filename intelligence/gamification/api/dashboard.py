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

from core.cache import redis_client

router = APIRouter()


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


def build_affiliations(conn, user_id: int):
    suggestions = []

    finance = conn.execute(
        text("""
            SELECT type, COALESCE(SUM(amount), 0) AS total
            FROM finance_items
            WHERE user_id = :user_id
            GROUP BY type
        """),
        {"user_id": user_id}
    ).fetchall()

    totals = {row.type: float(row.total or 0) for row in finance}

    if totals.get("epargne", 0) < max(totals.get("charges", 0), 1):
        suggestions.append({
            "title": "Compte epargne ou cash management",
            "reason": "Renforcer le matelas de securite avant de prendre plus de risque.",
            "priority": "high",
        })

    if totals.get("dettes", 0) > totals.get("epargne", 0):
        suggestions.append({
            "title": "Courtier credit / restructuration",
            "reason": "Optimiser le cout de la dette peut liberer du cashflow.",
            "priority": "medium",
        })

    suggestions.append({
        "title": "Plateforme d'investissement adaptee au profil",
        "reason": "Comparer les frais, la liquidite et les supports avant allocation.",
        "priority": "medium",
    })

    return suggestions[:3]


def build_gamification_actions(score: float, level):
    actions = []

    if score >= 70:
        actions.append({
            "title": "Mission Advanced",
            "description": "Choisir une opportunite prioritaire et definir une action executable en 7 jours.",
            "xp": 150,
        })
        actions.append({
            "title": "Optimisation portefeuille",
            "description": "Verifier la plus forte exposition et reduire le risque si elle depasse ton seuil.",
            "xp": 120,
        })
    else:
        actions.append({
            "title": "Base financiere",
            "description": "Completer revenus, charges, dettes et epargne pour debloquer plus de signaux.",
            "xp": 100,
        })

    return actions


def build_upgrade(score: float, level):
    level_text = str(level or "").upper()

    if score >= 70 or level_text in ["ADVANCED", "ELITE", "LIBERTY", "LEGACY"]:
        return {
            "recommended_plan": "elite",
            "title": "Passer au plan Elite - Wealth OS",
            "description": "Ton niveau justifie multi-user, gouvernance, IA premium et consolidation patrimoniale.",
        }

    return {
        "recommended_plan": "gold",
        "title": "Debloquer Gold - Growth",
        "description": "Acceder au portefeuille avance, immobilier, analytics, opportunites et recommandations IA.",
    }


# =========================
# GET USER ID
# =========================
def get_user_id(conn, email: str):
    row = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    return row.id if row else None


# =========================
# READ ONLY GAMIFICATION API (CACHE OPTIMIZED)
# =========================
@router.get("/")
@router.get("/gamification")
def get_gamification(user=Depends(get_current_user)):

    email = user.get("email") if isinstance(user, dict) else user

    cache_key = f"gamification:{email}"

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    with engine.connect() as conn:

        user_id = get_user_id(conn, email)

        # =========================
        # FALLBACK SAFE RESPONSE
        # =========================
        default_response = {
            "xp": 0,
            "level": 1,
            "streak": 0,
            "badges": [],
            "actions": build_gamification_actions(0, "FREE"),
            "upgrade": build_upgrade(0, "FREE"),
            "ai_coach": {
                "message": "Ajoute tes donnees pour recevoir des affiliations pertinentes.",
                "affiliations": [],
            },
        }

        if not user_id:
            set_cache(cache_key, default_response, ttl=60)
            return default_response

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
            "upgrade": build_upgrade(row.xp or 0, row.level or 1),
            "ai_coach": {
                "message": (
                    "Je te propose les prochaines actions et affiliations en "
                    "fonction de ta situation, de ton score et de tes objectifs."
                ),
                "affiliations": build_affiliations(conn, user_id),
            }
        }

        # =========================
        # CACHE STORE
        # =========================
        set_cache(cache_key, result, ttl=300)

        return result
