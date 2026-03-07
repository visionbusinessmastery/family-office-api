# ==================================================
# IMPORTS
# ==================================================

from fastapi import FastAPI
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

app = FastAPI(
    title="Family Office IA",
    version="5.0"
)

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

        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True
        )

        with engine.begin() as conn:

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE,
                    revenus FLOAT,
                    charges FLOAT,
                    patrimoine FLOAT,
                    score INT,
                    profil TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

    except Exception as e:

        print("DB INIT ERROR:", e)


# ==================================================
# CACHE API
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

        cache[url] = {
            "data": data,
            "time": time.time()
        }

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

    patrimoine = (
        profile.epargne +
        profile.immobilier +
        profile.investissements +
        profile.crypto
    )

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
# ALLOCATION PORTEFEUILLE
# ==================================================

def generate_allocation(risque):

    if risque == "Prudent":

        return {
            "actions": 40,
            "obligations": 40,
            "immobilier": 15,
            "liquidites": 5
        }

    if risque == "Modéré":

        return {
            "actions": 60,
            "obligations": 20,
            "immobilier": 15,
            "liquidites": 5
        }

    return {
        "actions": 80,
        "obligations": 5,
        "immobilier": 10,
        "liquidites": 5
    }


# ==================================================
# ANALYSE ACTION
# ==================================================

def analyse_investissement(price, change):

    change_value = float(change.replace("%", ""))

    if change_value > 2:

        signal = "momentum haussier"
        strategie = "surveiller breakout"
        trend = "bullish"

    elif change_value < -2:

        signal = "correction court terme"
        strategie = "achat progressif possible"
        trend = "bearish court terme"

    else:

        signal = "stabilisation"
        strategie = "attendre confirmation"
        trend = "neutre"

    return {
        "trend": trend,
        "signal": signal,
        "strategie": strategie
    }


# ==================================================
# SCORE ACTION
# ==================================================

def score_action(price, change):

    score = 50

    change_value = float(change.replace("%", ""))

    if change_value > 3:

        score += 20

    elif change_value > 1:

        score += 10

    elif change_value < -3:

        score -= 20

    elif change_value < -1:

        score -= 10

    return max(0, min(score, 100))


# ==================================================
# RATING ACTION
# ==================================================

def rating_action(score):

    if score >= 70:
        return "BUY"

    elif score >= 50:
        return "HOLD"

    return "SELL"


# ==================================================
# ROUTE ROOT
# ==================================================

@app.get("/")
def root():

    return {
        "status": "API active",
        "version": "5.0"
    }


# ==================================================
# PROFIL INVESTISSEUR
# ==================================================

@app.post("/profile")
def save_profile(profile: ProfileRequest):

    score = calculate_score(profile)

    allocation = generate_allocation(profile.risque)

    patrimoine = (
        profile.epargne +
        profile.immobilier +
        profile.investissements +
        profile.crypto
    )

    if engine and profile.email:

        try:

            with engine.begin() as conn:

                conn.execute(text("""

                    INSERT INTO users (email, revenus, charges, patrimoine, score, profil)

                    VALUES (:email, :revenus, :charges, :patrimoine, :score, :profil)

                    ON CONFLICT (email) DO UPDATE

                    SET score=:score, patrimoine=:patrimoine

                """), {

                    "email": profile.email,
                    "revenus": profile.revenus,
                    "charges": profile.charges,
                    "patrimoine": patrimoine,
                    "score": score,
                    "profil": profile.risque

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
# ANALYSE ACTION
# ==================================================

@app.post("/stocks/analyse")
def analyse_stock(request: StockRequest):

    if not ALPHA_VANTAGE_API_KEY:
        return {"error": "Clé API manquante"}

    ticker = request.ticker.upper()

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"

    data = get_cached(url)

    if not data or "Global Quote" not in data:
        return {"error": "Données indisponibles"}

    quote = data["Global Quote"]

    price = quote.get("05. price")
    change = quote.get("10. change percent")

    if not price:
        return {"error": "Prix indisponible"}

    # =============================
    # SCORE MOMENTUM
    # =============================

    change_value = float(change.replace("%", ""))

    momentum_score = 50

    if change_value > 3:
        momentum_score += 30
    elif change_value > 1:
        momentum_score += 15
    elif change_value < -3:
        momentum_score -= 30
    elif change_value < -1:
        momentum_score -= 15

    momentum_score = max(0, min(momentum_score, 100))

    # =============================
    # SCORE FINAL
    # =============================

    final_score = momentum_score

    # Rating automatique

    if final_score >= 70:
        rating = "BUY"
    elif final_score >= 50:
        rating = "HOLD"
    else:
        rating = "SELL"

    return {
        "ticker": ticker,
        "price": float(price),
        "change_percent": change,
        "momentum_score": momentum_score,
        "final_score": final_score,
        "rating": rating,
        "source": "Alpha Vantage"
    }

# ==================================================
# STOCK PICKER
# ==================================================

@app.get("/stockpicker")
def stockpicker():

    if not ALPHA_VANTAGE_API_KEY:
        return {"stocks": []}

    symbols = ["TSLA", "AAPL", "MSFT", "NVDA"]

    results = []

    for symbol in symbols:

        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"

        data = get_cached(url)

        if data and "Global Quote" in data:

            quote = data["Global Quote"]

            price = quote.get("05. price")
            change = quote.get("10. change percent")

            if price and change:

                # Calcul du momentum
                momentum = analyse_investissement(price, change)

                # Score
                momentum_score = score_action(price, change)

                # Rating
                rating = rating_action(momentum_score)

                results.append({
                    "symbol": symbol,
                    "price": float(price),
                    "change": change,
                    "momentum": momentum,
                    "momentum_score": momentum_score,
                    "rating": rating
                })

    return {"stocks": results}

# ==================================================
# IA BRAIN
# ==================================================

@app.post("/ia/brain")
def brain(request: BrainRequest):

    question = request.question.lower()

    # =========================
    # DÉTECTION D’INTENTION
    # =========================

    investissement_keywords = [
        "investir", "investissement", "action", "actions",
        "bourse", "marché", "acheter", "opportunité",
        "etf", "portefeuille"
    ]

    crypto_keywords = ["crypto", "bitcoin", "ethereum", "blockchain"]

    business_keywords = ["business", "entreprise", "startup", "saaS"]

    real_estate_keywords = ["immobilier", "location", "rendement locatif"]

    # =========================
    # LOGIQUE INTELLIGENTE
    # =========================

    if any(word in question for word in investissement_keywords):

        return {
            "theme": "Stratégie d’Investissement",
            "niveau": "Avancé",
            "analyse": {
                "resume": "Opportunité d’optimisation de portefeuille détectée.",
                "contexte": "Marchés dynamiques nécessitant diversification et gestion du risque.",
                "opportunite_generale": "Construction d’un portefeuille structuré."
            },
            "strategie": {
                "court_terme": "Éviter le sur-engagement, privilégier les positions progressives.",
                "moyen_terme": "Allocation sectorielle équilibrée.",
                "long_terme": "Capitalisation sur les tendances structurelles (IA, tech, énergie)."
            },
            "secteurs_prioritaires": [
                "Intelligence Artificielle",
                "Technologie",
                "Semi-conducteurs",
                "Énergies renouvelables",
                "ETF diversifiés"
            ],
            "gestion_du_risque": {
                "diversification": "Essentielle",
                "liquidites_recommandees": "5-20%",
                "horizon_suggere": "3 à 10 ans"
            }
        }

    if any(word in question for word in crypto_keywords):

        return {
            "theme": "Crypto & Blockchain",
            "niveau": "Intermédiaire",
            "analyse": "Marché volatil mais fort potentiel structurel.",
            "strategie": "Exposition limitée (5-10%).",
            "opportunites": ["Bitcoin", "Ethereum", "Infrastructure blockchain"],
            "gestion_du_risque": "Ne jamais surpondérer la crypto."
        }

    if any(word in question for word in business_keywords):

        return {
            "theme": "Entrepreneuriat",
            "niveau": "Stratégique",
            "analyse": "Création de valeur via actifs digitaux scalables.",
            "strategie": "Business automatisé à faible coût initial.",
            "opportunites": ["SaaS", "Agence IA", "Newsletter premium"],
            "levier": "Automatisation + Marketing digital"
        }

    if any(word in question for word in real_estate_keywords):

        return {
            "theme": "Immobilier",
            "analyse": "Actif stable générant cashflow.",
            "strategie": "Focus rendement + localisation.",
            "opportunites": ["Location meublée", "SCPI", "Immobilier international"]
        }

    # =========================
    # RÉPONSE PAR DÉFAUT INTELLIGENTE
    # =========================

    return {
        "theme": "Analyse Financière Globale",
        "niveau": "Général",
        "analyse": "Je peux analyser investissement, crypto, business ou immobilier.",
        "strategie": "Pose une question plus spécifique pour une recommandation ciblée.",
        "capacites": [
            "Analyse de portefeuille",
            "Stratégie long terme",
            "Gestion du risque",
            "Détection d’opportunités"
        ]
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

        return {

            "database": "error",
            "detail": str(e)

        }



