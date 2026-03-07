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
FMP_API_KEY = os.getenv("FMP_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="Family Office AI", version="7.0")

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
    if url in cache and time.time() - cache[url]["time"] < CACHE_DURATION:
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
# SCORE INVESTISSEUR
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

# ==================================================
# PROJECTION PATRIMONIALE
# ==================================================

def calculate_projection(patrimoine, allocation, years=10):

    returns = {
        "actions": 0.08,
        "obligations": 0.04,
        "immobilier": 0.06,
        "liquidites": 0.02
    }

    total = 0

    for asset, percent in allocation.items():
        if asset in returns:
            weight = percent / 100
            total += patrimoine * weight * ((1 + returns[asset]) ** years)

    return round(total, 2)

# ==================================================
# STOCK ANALYSE (ALPHA + FMP + SCORING)
# ==================================================

def calculate_advanced_score(change_percent, pe_ratio=None):

    score = 50

    try:
        change = float(change_percent.replace("%",""))

        if change > 3:
            score += 25
        elif change > 1:
            score += 10
        elif change < -3:
            score -= 25
        elif change < -1:
            score -= 10

        if pe_ratio:
            pe = float(pe_ratio)
            if 0 < pe < 20:
                score += 10
            elif pe > 40:
                score -= 10

    except:
        pass

    return max(0, min(score, 100))


def get_stock_data(ticker):

    ticker = ticker.upper()

    # Alpha Vantage
    alpha_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
    alpha_data = get_cached(alpha_url)
    alpha_quote = alpha_data.get("Global Quote", {}) if alpha_data else {}

    # FMP
    fmp_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
    fmp_data = get_cached(fmp_url)
    fmp_profile = fmp_data[0] if fmp_data else {}

    price = alpha_quote.get("05. price")
    change = alpha_quote.get("10. change percent")

    if not price:
        return None

    momentum_score = calculate_advanced_score(change, fmp_profile.get("pe"))

    if momentum_score >= 70:
        rating = "BUY"
    elif momentum_score >= 50:
        rating = "HOLD"
    else:
        rating = "SELL"

    return {
        "ticker": ticker,
        "price": float(price),
        "change_percent": change,
        "company": fmp_profile.get("companyName"),
        "sector": fmp_profile.get("sector"),
        "momentum_score": momentum_score,
        "rating": rating,
        "sources": ["Alpha Vantage", "FMP"]
    }

# ==================================================
# ROUTES
# ==================================================

@app.get("/")
def root():
    return {"status": "API active", "version": "7.0"}

# -------------------------
# STOCK ANALYSE
# -------------------------

@app.post("/stocks/analyse")
def analyse_stock(request: StockRequest):

    if not ALPHA_VANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="API Key manquante")

    data = get_stock_data(request.ticker)

    if not data:
        raise HTTPException(status_code=400, detail="Données indisponibles")

    return data

# -------------------------
# AI BRAIN ULTIME
# -------------------------

@app.post("/ia/brain")
def brain(request: BrainRequest):

    question = request.question.lower()

    # =========================
    # PROFIL UTILISATEUR
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

    if user_data:
        score = user_data["score"]
        patrimoine = user_data["patrimoine"]

        if score >= 75:
            niveau = "Family Office Stratégique"
            risk = "Élevé contrôlé"
        elif score >= 50:
            niveau = "Investisseur Équilibré"
            risk = "Modéré"
        else:
            niveau = "Investisseur Prudent"
            risk = "Faible"

    else:
        niveau = "Profil Non Défini"
        risk = "Standard"
        patrimoine = 0

    # =========================
    # DEVELOPPEMENT PATRIMOINE (VERSION PREMIUM)
    # =========================

    if any(word in question for word in ["patrimoine", "développer", "croissance", "capital", "richesse"]):

        allocation = {
            "actions": 60,
            "obligations": 20,
            "immobilier": 15,
            "liquidites": 5
        }

        projection_5 = calculate_projection(patrimoine, allocation, 5)
        projection_10 = calculate_projection(patrimoine, allocation, 10)

        return {
            "theme": "Stratégie d'Accroissement Patrimonial",
            "niveau_utilisateur": niveau,
            "patrimoine_actuel": patrimoine,
            "objectif_strategique": "Optimisation et effet composé long terme",

            "analyse": (
                "La croissance patrimoniale repose sur 4 piliers : "
                "augmentation des revenus, "
                "allocation stratégique du capital, "
                "réinvestissement systématique, "
                "et gestion du risque adaptée au profil."
            ),

            "strategie": {
                "leviers": [
                    "Investissement progressif automatisé (DCA)",
                    "Réinvestissement des dividendes",
                    "Diversification multi-actifs",
                    "Optimisation fiscale"
                ],
                "gestion_risque": risk
            },

            "allocation_recommandee": allocation,

            "plan_action": [
                "Constituer un fonds de sécurité (6 mois de charges)",
                "Mettre en place un investissement automatique mensuel",
                "Diversifier sur ETF larges marchés",
                "Suivre performance chaque mois",
                "Rééquilibrer annuellement"
            ],

            "projection_5_ans": projection_5,
            "projection_10_ans": projection_10,

            "score_confiance": 95,
            "niveau": "Stratégique"
        }

    # =========================
    # ACTIONS / MARCHÉS
    # =========================

    if any(word in question for word in ["action", "bourse", "marché", "investir", "2026"]):

        return {
            "theme": "Stratégie Marchés 2026",
            "niveau_utilisateur": niveau,

            "analyse": (
                "Les moteurs structurels 2026 sont : "
                "Intelligence Artificielle, "
                "Semi-conducteurs, Cloud, "
                "Cybersécurité, ETF globaux et énergies stratégiques."
            ),

            "strategie": {
                "approche": "Allocation en 3 piliers",
                "piliers": [
                    "Croissance technologique",
                    "ETF larges marchés",
                    "Secteurs défensifs"
                ],
                "adaptation_risque": risk
            },

            "allocation_recommandee": {
                "etf_large_marche": "30%",
                "actions_croissance": "30%",
                "secteurs_defensifs": "20%",
                "liquidites": "20%"
            },

            "score_confiance": 92,
            "niveau": "Stratégique"
        }

    # =========================
    # DEFAULT
    # =========================

    return {
        "theme": "Conseil Patrimonial Global",
        "niveau_utilisateur": niveau,
        "analyse": "Optimisation globale du capital selon profil.",
        "strategie": {
            "principe": "Diversification intelligente",
            "gestion_risque": risk
        },
        "score_confiance": 85,
        "niveau": "Professionnel"
    }

# -------------------------
# DB CHECK
# -------------------------

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

