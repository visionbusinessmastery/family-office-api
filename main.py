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

    question = request.question.lower()

    # =========================
    # 1️⃣ RECUPERATION PROFIL
    # =========================

    user_data = None

    if engine:
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT score, profil, patrimoine
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT 1
                """))
                row = result.fetchone()

                if row:
                    user_data = {
                        "score": row[0],
                        "profil": row[1],
                        "patrimoine": row[2]
                    }
        except:
            pass

    # =========================
    # 2️⃣ DÉTERMINATION NIVEAU
    # =========================

    if user_data:
        score = user_data["score"]

        if score >= 75:
            niveau = "Investisseur Stratégique"
            risk_level = "Élevé contrôlé"
            allocation_base = 80
        elif score >= 50:
            niveau = "Investisseur Équilibré"
            risk_level = "Modéré"
            allocation_base = 60
        else:
            niveau = "Investisseur Prudent"
            risk_level = "Faible"
            allocation_base = 40

    else:
        niveau = "Profil Non Défini"
        risk_level = "Standard"
        allocation_base = 50

    # =========================
    # 3️⃣ LOGIQUE MARCHÉS
    # =========================

    if any(word in question for word in ["action", "bourse", "marché", "investir"]):

        return {
            "theme": "Stratégie Marchés Financiers",
            "niveau_utilisateur": niveau,
            "analyse": (
                "Les marchés sont dominés par l’IA, "
                "la cybersécurité, les semi-conducteurs, "
                "le cloud et les énergies stratégiques."
            ),
            "strategie": {
                "approche": "Diversification intelligente en 3 piliers",
                "piliers": [
                    "Croissance technologique",
                    "ETF larges marchés",
                    "Secteurs défensifs"
                ],
                "adaptation_risque": risk_level
            },
            "allocation_recommandee": {
                "actions_croissance": f"{int(allocation_base * 0.4)}%",
                "etf_marches": f"{int(allocation_base * 0.3)}%",
                "secteurs_defensifs": f"{int(allocation_base * 0.2)}%",
                "liquidites": f"{100 - allocation_base}%"
            },
            "opportunites": [
                "ETF S&P 500",
                "ETF Nasdaq",
                "Actions IA",
                "Semi-conducteurs",
                "Cybersécurité",
                "Énergies renouvelables"
            ],
            "score_confiance": 90,
            "niveau": "Stratégique"
        }

    # =========================
    # 4️⃣ LOGIQUE CRYPTO
    # =========================

    if "crypto" in question:

        return {
            "theme": "Stratégie Crypto",
            "niveau_utilisateur": niveau,
            "analyse": (
                "La crypto doit rester une composante "
                "limitée et stratégique du portefeuille."
            ),
            "strategie": {
                "allocation_max": "5-10%",
                "objectif": "Diversification long terme",
                "gestion_risque": risk_level
            },
            "opportunites": [
                "Bitcoin",
                "Ethereum"
            ],
            "score_confiance": 85,
            "niveau": "Contrôlé"
        }

    # =========================
    # 5️⃣ REPONSE GLOBALE PREMIUM
    # =========================

    return {
        "theme": "Conseil Patrimonial Global",
        "niveau_utilisateur": niveau,
        "analyse": (
            "Optimisation globale du capital "
            "selon profil, horizon et tolérance au risque."
        ),
        "strategie": {
            "principe": "Diversification multi-actifs",
            "gestion_risque": risk_level,
            "adaptation_score": score if user_data else "N/A"
        },
        "opportunites": [
            "Actions",
            "ETF",
            "Obligations",
            "Immobilier"
        ],
        "score_confiance": 80,
        "niveau": "Professionnel"
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



