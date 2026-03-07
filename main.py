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

app = FastAPI(title="Family Office IA", version="6.1")

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
    return {"status": "API active", "version": "6.1"}

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
                """), {"email": profile.email, "score": score, "profil": profile.risque, "patrimoine": patrimoine})
        except Exception as e:
            print("DB ERROR:", e)

    return {"status": "ok", "score_investisseur": score, "allocation_recommandee": allocation, "patrimoine_total": patrimoine}

# ==================================================
# STOCK ANALYSE AVANCÉE (Alpha + FMP)
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
            if 0 < float(pe_ratio) < 20:
                score += 10
            elif float(pe_ratio) > 40:
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
    pe_ratio = fmp_profile.get("pe")

    if not price:
        return None

    momentum_score = calculate_advanced_score(change, pe_ratio)
    final_score = momentum_score

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
        "company": fmp_profile.get("companyName"),
        "sector": fmp_profile.get("sector"),
        "momentum_score": momentum_score,
        "final_score": final_score,
        "rating": rating,
        "sources": ["Alpha Vantage", "FMP"]
    }

@app.post("/stocks/analyse")
def analyse_stock(request: StockRequest):
    if not ALPHA_VANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="API Key manquante")
    data = get_stock_data(request.ticker)
    if not data:
        raise HTTPException(status_code=400, detail="Données indisponibles")
    return data

# ==================================================
# IA BRAIN — FAMILY OFFICE 2026
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
                    user_data = {"score": row[0], "profil": row[1], "patrimoine": row[2]}
        except:
            pass

    if user_data:
        score = user_data["score"]
        if score >= 75:
            niveau = "Investisseur Stratégique"
            risk_level = "Élevé contrôlé"
        elif score >= 50:
            niveau = "Investisseur Équilibré"
            risk_level = "Modéré"
        else:
            niveau = "Investisseur Prudent"
            risk_level = "Faible"
    else:
        niveau = "Profil Non Défini"
        risk_level = "Standard"

    # Actions / Marché 2026
    if any(word in question for word in ["action","bourse","marché","investir","2026"]):
        return {
            "theme": "Stratégie Marchés 2026",
            "niveau_utilisateur": niveau,
            "analyse": (
                "Les tendances majeures 2026 sont : Intelligence Artificielle, "
                "Semi-conducteurs, Cloud computing, Cybersécurité, "
                "Énergies stratégiques et ETF globaux."
            ),
            "strategie": {
                "approche": "Allocation en 3 piliers",
                "piliers": [
                    "Croissance technologique (IA, semi-conducteurs)",
                    "ETF larges marchés (S&P 500, Nasdaq)",
                    "Secteurs défensifs (santé, énergie, consommation)"
                ],
                "adaptation_risque": risk_level
            },
            "allocation_recommandee": {
                "etf_large_marche": "30%",
                "actions_croissance": "30%",
                "secteurs_defensifs": "20%",
                "liquidites": "20%"
            },
            "opportunites_precises_2026": [
                "ETF S&P 500 (SPY / VOO)",
                "ETF Nasdaq 100 (QQQ)",
                "ETF Intelligence Artificielle",
                "NVIDIA (Semi-conducteurs)",
                "Microsoft (Cloud & IA)",
                "Apple (Écosystème)",
                "ETF Cybersécurité",
                "ETF Énergies renouvelables"
            ],
            "score_confiance": 92,
            "niveau": "Stratégique"
        }

    # Crypto
    if "crypto" in question:
        return {
            "theme": "Stratégie Crypto 2026",
            "niveau_utilisateur": niveau,
            "analyse": "Marché volatil mais structurellement en croissance.",
            "strategie": {
                "allocation_max_recommandee": "5-10%",
                "objectif": "Diversification long terme"
            },
            "opportunites": ["Bitcoin", "Ethereum"],
            "score_confiance": 85,
            "niveau": "Contrôlé"
        }

    # Réponse par défaut
    return {
        "theme": "Conseil Patrimonial Global",
        "niveau_utilisateur": niveau,
        "analyse": "Optimisation globale du capital selon profil.",
        "strategie": {"principe":"Diversification intelligente", "gestion_risque": risk_level},
        "opportunites":["Actions","ETF","Obligations","Immobilier"],
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
