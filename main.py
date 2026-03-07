from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
def analyse_investissement(price, change):

    change_value = float(change.replace("%",""))

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

import os
import time
from datetime import datetime
from sqlalchemy import create_engine, text

# ==================================================
# CONFIG
# ==================================================

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="Family Office IA", version="5.0")

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
# CACHE
# ==================================================

cache = {}
CACHE_DURATION = 900  # 15 min

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
# UTILITAIRES
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
# ROUTES
# ==================================================

@app.get("/")
def root():
    return {"status": "API active"}

# -------------------------
# PROFIL
# -------------------------

@app.post("/profile")
def save_profile(profile: ProfileRequest):

    score = calculate_score(profile)
    allocation = generate_allocation(profile.risque)

    patrimoine = profile.epargne + profile.immobilier + profile.investissements + profile.crypto

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

# -------------------------
# ANALYSE ACTION (ALPHA)
# -------------------------

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

    analyse = analyse_investissement(price, change)

    return {
        "ticker": ticker,
        "price": float(price),
        "change_percent": change,
        "source": "Alpha Vantage",
        "analyse": analyse
    }

# -------------------------
# STOCK PICKER SIMPLE
# -------------------------

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

            results.append({
                "symbol": symbol,
                "price": quote.get("05. price"),
                "change": quote.get("10. change percent")
            })

    return {"stocks": results}

# -------------------------
# IA BRAIN
# -------------------------

@app.post("/ia/brain")
def brain(request: BrainRequest):

    question = request.question.lower()

    if "investir" in question:

        return {
            "theme": "Investissement",
            "analyse": "Diversification recommandée.",
            "strategie": "Long terme progressif.",
            "opportunites": ["Actions IA", "ETF", "Immobilier"]
        }

    return {
        "theme": "Général",
        "analyse": "Analyse stratégique.",
        "strategie": "Gestion du risque.",
        "opportunites": ["Diversification"]
    }

# -------------------------
# DATABASE CHECK
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



