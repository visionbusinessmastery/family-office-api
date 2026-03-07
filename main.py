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

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    id SERIAL PRIMARY KEY,
                    user_email TEXT,
                    asset TEXT,
                    asset_type TEXT,
                    quantity FLOAT,
                    buy_price FLOAT,
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

        if r.status_code != 200:
            return None

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


class PortfolioRequest(BaseModel):
    email: str
    asset: str
    asset_type: str
    quantity: float
    buy_price: float


# ==================================================
# SCORE INVESTISSEUR
# ==================================================

def calculate_score(profile):

    score = 0

    capacite = profile.revenus - profile.charges
    patrimoine = (
        profile.epargne
        + profile.immobilier
        + profile.investissements
        + profile.crypto
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
# STOCK ANALYSE
# ==================================================

def calculate_advanced_score(change_percent, pe_ratio=None):

    score = 50

    try:

        change = float(change_percent.replace("%", ""))

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

    if not ALPHA_VANTAGE_API_KEY or not FMP_API_KEY:
        raise HTTPException(status_code=500, detail="API Keys manquantes")

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


# ==================================================
# PORTFOLIO
# ==================================================

@app.post("/portfolio/add")
def add_asset(request: PortfolioRequest):

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    try:

        with engine.begin() as conn:

            conn.execute(text("""
                INSERT INTO portfolios (user_email, asset, asset_type, quantity, buy_price)
                VALUES (:email, :asset, :asset_type, :quantity, :buy_price)
            """), {
                "email": request.email,
                "asset": request.asset,
                "asset_type": request.asset_type,
                "quantity": request.quantity,
                "buy_price": request.buy_price
            })

        return {"status": "actif ajouté", "asset": request.asset}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio/{email}")
def get_portfolio(email: str):

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    try:

        with engine.connect() as conn:

            result = conn.execute(text("""
                SELECT asset, asset_type, quantity, buy_price
                FROM portfolios
                WHERE user_email = :email
            """), {"email": email})

            rows = result.fetchall()

            portfolio = []

            for r in rows:

                portfolio.append({
                    "asset": r[0],
                    "type": r[1],
                    "quantity": r[2],
                    "buy_price": r[3]
                })

            return {
                "email": email,
                "portfolio": portfolio
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================================================
# STOCK ANALYSE
# ==================================================

@app.post("/stocks/analyse")
def analyse_stock(request: StockRequest):

    if not ALPHA_VANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="API Key manquante")

    data = get_stock_data(request.ticker)

    if not data:
        raise HTTPException(status_code=400, detail="Données indisponibles")

    return data


# ==================================================
# AI BRAIN
# ==================================================

@app.post("/ia/brain")
def brain(request: BrainRequest):

    question = request.question.lower()

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


# ==================================================
# DB CHECK
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


