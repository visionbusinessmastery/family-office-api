from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import os
import time
from sqlalchemy import create_engine, text

# ==================================================
# CONFIG
# ==================================================

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="Family Office IA", version="6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================
# DATABASE
# ==================================================

engine = None

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)

        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE,
                    score INT,
                    profil TEXT,
                    patrimoine FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

    except Exception as e:
        print("DB INIT ERROR:", e)

# ==================================================
# CACHE
# ==================================================

cache = {}
CACHE_DURATION = 900

def get_cached(url):

    if url in cache:
        if time.time() - cache[url]["time"] < CACHE_DURATION:
            return cache[url]["data"]

    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        cache[url] = {"data": data, "time": time.time()}
        return data
    except:
        return None

# ==================================================
# MODELS
# ==================================================

class ProfileRequest(BaseModel):
    email: Optional[str] = None
    revenus: float
    charges: float
    epargne: float
    immobilier: float
    investissements: float
    crypto: float
    risque: str
    experience: str

class StockRequest(BaseModel):
    ticker: str

class BrainRequest(BaseModel):
    question: str

# ==================================================
# LOGIQUE SCORE
# ==================================================

def calculate_score(profile):

    score = 0

    capacite = profile.revenus - profile.charges
    patrimoine = profile.epargne + profile.immobilier + profile.investissements + profile.crypto

    if capacite > 0:
        score += 30

    if patrimoine > 100000:
        score += 30

    if profile.experience == "Avancé":
        score += 20
    elif profile.experience == "Intermédiaire":
        score += 10

    if profile.risque == "Dynamique":
        score += 20

    return min(score, 100)

def generate_allocation(risque):

    if risque == "Prudent":
        return {"actions": 40, "obligations": 40, "immobilier": 15, "liquidites": 5}

    if risque == "Modéré":
        return {"actions": 60, "obligations": 20, "immobilier": 15, "liquidites": 5}

    return {"actions": 80, "obligations": 5, "immobilier": 10, "liquidites": 5}

# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():
    return {"status": "API active", "version": "6.0"}

# ==================================================
# PROFILE
# ==================================================

@app.post("/profile")
def save_profile(profile: ProfileRequest):

    score = calculate_score(profile)
    allocation = generate_allocation(profile.risque)

    patrimoine = profile.epargne + profile.immobilier + profile.investissements + profile.crypto

    if engine and profile.email:

        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO users (email, score, profil, patrimoine)
                    VALUES (:email, :score, :profil, :patrimoine)
                    ON CONFLICT (email)
                    DO UPDATE SET score=:score, patrimoine=:patrimoine
                """), {
                    "email": profile.email,
                    "score": score,
                    "profil": profile.risque,
                    "patrimoine": patrimoine
                })
        except Exception as e:
            print("DB ERROR:", e)

    return {
        "status": "ok",
        "score_investisseur": score,
        "allocation_recommandee": allocation,
        "patrimoine_total": patrimoine
    }

# ==================================================
# STOCK ANALYSE
# ==================================================

@app.post("/stocks/analyse")
def analyse_stock(request: StockRequest):

    if not ALPHA_VANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="Clé API manquante")

    ticker = request.ticker.upper()

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"

    data = get_cached(url)

    if not data or "Global Quote" not in data:
        raise HTTPException(status_code=400, detail="Données indisponibles")

    quote = data["Global Quote"]

    price = quote.get("05. price")
    change = quote.get("10. change percent")

    if not price:
        raise HTTPException(status_code=400, detail="Prix indisponible")

    change_value = float(change.replace("%",""))

    # Momentum
    if change_value > 2:
        trend = "bullish"
        signal = "momentum haussier"
        rating = "BUY"
        momentum_score = 80

    elif change_value < -2:
        trend = "bearish"
        signal = "correction"
        rating = "SELL"
        momentum_score = 30

    else:
        trend = "neutral"
        signal = "stabilisation"
        rating = "HOLD"
        momentum_score = 50

    final_score = momentum_score

    return {
        "ticker": ticker,
        "price": float(price),
        "change_percent": change,
        "momentum_score": momentum_score,
        "final_score": final_score,
        "rating": rating,
        "source": "Alpha Vantage",
        "analyse": {
            "trend": trend,
            "signal": signal
        }
    }

# ==================================================
# AI BRAIN (VERSION AMÉLIORÉE)
# ==================================================

@app.post("/ia/brain")
def brain(request: BrainRequest):

    q = request.question.lower()

    # ==============================
    # INVESTISSEMENT ACTIONS
    # ==============================

    if "action" in q or "bourse" in q or "investir" in q:

        return {
            "theme": "Stratégie Marchés Financiers",
            "analyse": "Les marchés 2026 sont dominés par l'IA, la cybersécurité, les semi-conducteurs et les infrastructures cloud.",
            "strategie": "Approche en 3 piliers : croissance, diversification et gestion du risque.",
            "allocation_recommandee": {
                "etf_technologie": "30%",
                "actions_croissance": "30%",
                "secteurs_defensifs": "20%",
                "liquidites": "20%"
            },
            "opportunites": [
                "ETF S&P 500",
                "ETF Nasdaq",
                "Actions IA",
                "Semi-conducteurs",
                "Cybersécurité",
                "Énergies renouvelables"
            ],
            "niveau": "Stratégique"
        }

    # ==============================
    # CRYPTO
    # ==============================

    if "crypto" in q or "bitcoin" in q:

        return {
            "theme": "Stratégie Crypto",
            "analyse": "La crypto reste un actif volatil mais stratégique dans une allocation moderne.",
            "strategie": "Limiter l'exposition à 5-10% du portefeuille.",
            "allocation_recommandee": {
                "bitcoin": "50%",
                "ethereum": "30%",
                "altcoins_selectionnes": "20%"
            },
            "opportunites": [
                "Bitcoin",
                "Ethereum",
                "Infrastructure blockchain",
                "Tokenisation d'actifs"
            ],
            "niveau": "Tactique"
        }

    # ==============================
    # ENTREPRENEURIAT
    # ==============================

    if "business" in q or "entreprendre" in q:

        return {
            "theme": "Création de Richesse",
            "analyse": "L'effet levier digital est la clé de la croissance patrimoniale.",
            "strategie": "Créer des actifs scalables (digital, IA, automatisation).",
            "opportunites": [
                "Agence IA",
                "SaaS",
                "Formation en ligne",
                "Automatisation business"
            ],
            "niveau": "Vision long terme"
        }

    # ==============================
    # RÉPONSE STRATÉGIQUE GÉNÉRALE
    # ==============================

    return {
        "theme": "Conseil Patrimonial Global",
        "analyse": "Optimisation du capital via diversification multi-actifs.",
        "strategie": "Répartition équilibrée entre croissance, protection et liquidité.",
        "allocation_type": "Adaptée au profil investisseur",
        "opportunites": [
            "ETF mondiaux",
            "Immobilier",
            "Obligations",
            "Actions internationales"
        ],
        "niveau": "Fondation"
    }

# ==================================================
# DATABASE CHECK
# ==================================================

@app.get("/db-check")
def db_check():

    if not engine:
        return {"database": "not configured"}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as e:
        return {"database": "error", "detail": str(e)}

