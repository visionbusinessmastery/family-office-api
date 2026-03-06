from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import os
import time
from sqlalchemy import create_engine, text

# ======================
# CONFIG
# ======================

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="Family Office IA", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# DATABASE (SAFE)
# ======================

engine = None

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    except:
        engine = None

# ======================
# CREATION TABLES
# ======================

def init_db():

    try:

        with engine.connect() as conn:

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

            conn.commit()

    except Exception as e:
        print("DB init error:", e)


init_db()

# ======================
# STOCKAGE SIMPLE
# ======================

user_profile = {}
cache = {}
CACHE_DURATION = 900  # 15 min

# ======================
# MODELS
# ======================

class IARequest(BaseModel):
    message: str


class ProfileRequest(BaseModel):
    revenus: float
    charges_fixes: float
    charges_variables: float

    epargne_cash: float
    epargne_bloquee: float
    immobilier: float
    investissements: float
    crypto: float

    objectif: str
    horizon: int
    risque: str

    age: int
    pays: str
    experience: str

# ======================
# UTILITAIRES
# ======================

def get_market_data(url):

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


def calculate_investor_score(profile):

    score = 0

    capacite = profile.revenus - (profile.charges_fixes + profile.charges_variables)

    if capacite > 0:
        score += 25

    if profile.revenus > 0:
        taux = capacite / profile.revenus
        if taux > 0.2:
            score += 25
        elif taux > 0.1:
            score += 15

    patrimoine = (
        profile.epargne_cash +
        profile.epargne_bloquee +
        profile.immobilier +
        profile.investissements +
        profile.crypto
    )

    if patrimoine > 100000:
        score += 25

    if profile.experience == "Avancé":
        score += 25
    elif profile.experience == "Intermédiaire":
        score += 15

    return min(score, 100)


def generate_allocation(risque):

    if risque == "Prudent":
        return {"actions": 40, "obligations": 40, "immobilier": 15, "liquidites": 5}

    if risque == "Modéré":
        return {"actions": 60, "obligations": 20, "immobilier": 15, "liquidites": 5}

    return {"actions": 80, "obligations": 5, "immobilier": 10, "liquidites": 5}


def generate_psych_profile(score):

    if score < 40:
        return "Investisseur prudent débutant"

    if score < 70:
        return "Investisseur en croissance"

    return "Investisseur stratégique avancé"

# ======================
# ROUTES
# ======================

@app.get("/")
def root():
    return {"status": "API active"}


@app.post("/profile")
def save_profile(profile: ProfileRequest):

    global user_profile
    user_profile = profile

    score = calculate_investor_score(profile)

    allocation = generate_allocation(profile.risque)

    psych = generate_psych_profile(score)

    capacite = profile.revenus - (profile.charges_fixes + profile.charges_variables)

    patrimoine_total = (
        profile.epargne_cash +
        profile.epargne_bloquee +
        profile.immobilier +
        profile.investissements +
        profile.crypto
    )

    return {
        "status": "ok",
        "score_investisseur": score,
        "profil_psychologique": psych,
        "allocation_recommandee": allocation,
        "capacite_investissement": capacite,
        "patrimoine_total": patrimoine_total
    }


@app.post("/stocks/analyse")
def analyse_action(data: dict):

    ticker = data.get("ticker")

    if not ticker:
        return {"error": "Ticker manquant"}

    if not API_KEY:
        return {"error": "Clé API manquante"}

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker.upper()}&apikey={API_KEY}"

    data_json = get_market_data(url)

    if not data_json or "Global Quote" not in data_json:
        return {"error": "Données indisponibles"}

    quote = data_json["Global Quote"]

    return {
        "ticker": ticker.upper(),
        "prix": quote.get("05. price"),
        "variation": quote.get("10. change percent"),
        "source": "Alpha Vantage"
    }


@app.get("/stockpicker")
def stock_picker():

    if not API_KEY:
        return {"top_stocks": []}

    url = f"https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey={API_KEY}"

    data = get_market_data(url)

    if not data:
        return {"top_stocks": []}

    gainers = data.get("top_gainers", [])

    top_stocks = []

    for stock in gainers[:5]:

        top_stocks.append({
            "symbol": stock.get("ticker"),
            "price": stock.get("price"),
            "change": stock.get("change_percentage")
        })

    return {"top_stocks": top_stocks}

# ======================
# CREER UTILISATEUR
# ======================

class UserCreate(BaseModel):

    email: str
    revenus: float
    charges: float

    epargne: float
    immobilier: float
    investissements: float
    crypto: float


@app.post("/user/create")
def create_user(user: UserCreate):

    try:

        patrimoine = (
            user.epargne +
            user.immobilier +
            user.investissements +
            user.crypto
        )

        capacite = user.revenus - user.charges

        score = 0

        if capacite > 0:
            score += 40

        if patrimoine > 100000:
            score += 30

        if capacite > user.revenus * 0.2:
            score += 30

        # profil psychologique

        if score < 40:
            profil = "Prudent"
        elif score < 70:
            profil = "Équilibré"
        else:
            profil = "Dynamique"

        with engine.connect() as conn:

            conn.execute(text("""
                INSERT INTO users (email, revenus, charges, patrimoine, score, profil)
                VALUES (:email, :revenus, :charges, :patrimoine, :score, :profil)
            """), {

                "email": user.email,
                "revenus": user.revenus,
                "charges": user.charges,
                "patrimoine": patrimoine,
                "score": score,
                "profil": profil

            })

            conn.commit()

        return {
            "status": "user_created",
            "email": user.email,
            "score": score,
            "profil": profil,
            "patrimoine": patrimoine
        }

    except Exception as e:

        return {
            "error": str(e)
        }
        
@app.get("/db-check")
def db_check():

    if not engine:
        return {"database": "not configured"}

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return {"database": "connected"}
    except Exception as e:
        return {"database": "error", "detail": str(e)}


