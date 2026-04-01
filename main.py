from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy import create_engine, text
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
import requests
import os
import time
import yfinance as yf

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from pydantic import BaseModel
from sqlalchemy import text

# ==================================================
# CONFIG
# ==================================================

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

router = APIRouter()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

app = FastAPI(title="Family Office AI", version="10.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class Asset(BaseModel):
    asset: str
    asset_type: str
    quantity: float
    buy_price: float
    

class PortfolioRequest(BaseModel):
    asset: str
    asset_type: str
    quantity: float
    buy_price: float


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

class ProfileRequest(BaseModel):
    gender: str
    age: int

    employment_status: str
    monthly_income: float

    marital_status: str
    children_count: int

    housing_status: str
    real_estate_value: float = 0
    real_estate_purchase_price: float = 0

    total_debt: float = 0

    savings: float = 0
    investments: float = 0
    crypto: float = 0

    risk_profile: str

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
                email TEXT UNIQUE NOT NULL,
                password TEXT,
                revenus NUMERIC DEFAULT 0,
                charges NUMERIC DEFAULT 0,
                patrimoine NUMERIC DEFAULT 0,
                score INTEGER DEFAULT 0,
                profil TEXT,
                role TEXT DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_email, asset)
            )
            """))

            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id SERIAL PRIMARY KEY,
                user_email TEXT UNIQUE,

                gender TEXT,
                age INTEGER,

                employment_status TEXT,
                monthly_income FLOAT,

                marital_status TEXT,
                children_count INTEGER,

                housing_status TEXT,
                real_estate_value FLOAT,
                real_estate_purchase_price FLOAT,

                total_debt FLOAT,

                savings FLOAT,
                investments FLOAT,
                crypto FLOAT,

                risk_profile TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """))
            
       # 🔥 Nettoyage des doublons au démarrage
            conn.execute(text("""
            DELETE FROM portfolios a
                USING portfolios b
                WHERE a.ctid < b.ctid
                AND a.user_email = b.user_email
                AND a.asset = b.asset;
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

        cache[url] = {"data": data, "time": time.time()}
        return data

    except:
        return None

# ==================================================
# AUTH
# ==================================================

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Token invalide")

        return email

    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

# ==================================================
# AUTH ROUTES
# ==================================================

@app.post("/register")
def register(user: UserRegister):
    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    email = user.email.lower()
    hashed_password = hash_password(user.password)

    with engine.begin() as conn:
        result = conn.execute(text("SELECT email FROM users WHERE email=:email"), {"email": email})

        if result.fetchone():
            raise HTTPException(status_code=400, detail="Utilisateur déjà existant")

        conn.execute(text("""
            INSERT INTO users (email, password)
            VALUES (:email, :password)
        """), {"email": email, "password": hashed_password})

    return {"status": "Utilisateur créé"}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    email = form_data.username.lower()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT password FROM users WHERE email=:email"), {"email": email})
        row = result.fetchone()

        if not row or not verify_password(form_data.password, row[0]):
            raise HTTPException(status_code=400, detail="Identifiants invalides")

    token = create_token({"sub": email})

    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}

@app.post("/profile")
def save_profile(data: ProfileRequest, user: str = Depends(get_current_user)):

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO user_profiles (
                user_email, gender, age, employment_status, monthly_income,
                marital_status, children_count, housing_status,
                real_estate_value, real_estate_purchase_price,
                total_debt, savings, investments, crypto, risk_profile
            )
            VALUES (
                :email, :gender, :age, :employment_status, :monthly_income,
                :marital_status, :children_count, :housing_status,
                :real_estate_value, :real_estate_purchase_price,
                :total_debt, :savings, :investments, :crypto, :risk_profile
            )
            ON CONFLICT (user_email)
            DO UPDATE SET
                gender=:gender,
                age=:age,
                employment_status=:employment_status,
                monthly_income=:monthly_income,
                marital_status=:marital_status,
                children_count=:children_count,
                housing_status=:housing_status,
                real_estate_value=:real_estate_value,
                real_estate_purchase_price=:real_estate_purchase_price,
                total_debt=:total_debt,
                savings=:savings,
                investments=:investments,
                crypto=:crypto,
                risk_profile=:risk_profile,
                updated_at = CURRENT_TIMESTAMP
        """), {
            "email": user,
            **data.dict()
        })

    return {"status": "profil sauvegardé"}

@app.get("/profile")
def get_profile(user: str = Depends(get_current_user)):

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM user_profiles WHERE user_email=:email
        """), {"email": user})

        row = result.fetchone()

    if not row:
        return {"profile": None}

    return {"profile": dict(row._mapping)}   


# ==================================================
# STOCK DATA
# ==================================================

COMPANY_TO_TICKER = {
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "apple": "AAPL",
    "amazon": "AMZN",
    "microsoft": "MSFT",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "phunware": "PHUN",
}

def normalize_ticker(input_value: str):
    value = input_value.lower().strip()

    # 1. vérifier si c’est un nom connu
    if value in COMPANY_TO_TICKER:
        return COMPANY_TO_TICKER[value]

    # 2. sinon considérer que c’est un ticker
    return value.upper()


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


def get_stock_data(ticker: str):

    ticker = normalize_ticker(ticker)

    # =========================
    # 1. TRY ALPHA VANTAGE
    # =========================
    if ALPHA_VANTAGE_API_KEY:

        try:
            alpha_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
            alpha_data = get_cached(alpha_url)

            alpha_quote = alpha_data.get("Global Quote", {}) if alpha_data else {}

            price = alpha_quote.get("05. price")
            change = alpha_quote.get("10. change percent")

            if price:
                return {
                    "ticker": ticker,
                    "price": float(price),
                    "change_percent": change,
                    "source": "Alpha Vantage"
                }

        except:
            pass

    # =========================
    # 2. TRY FMP
    # =========================
    if FMP_API_KEY:

        try:
            fmp_url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={FMP_API_KEY}"
            fmp_data = get_cached(fmp_url)

            if fmp_data and len(fmp_data) > 0:
                stock = fmp_data[0]

                return {
                    "ticker": ticker,
                    "price": stock.get("price"),
                    "change_percent": str(stock.get("changesPercentage")) + "%",
                    "market_cap": stock.get("marketCap"),
                    "source": "FMP"
                }

        except:
            pass

    # =========================
    # 3. FINAL FALLBACK YFINANCE
    # =========================
    try:
       stock = yf.Ticker(ticker)
       info = stock.info

       price = info.get("currentPrice") or info.get("regularMarketPrice")

       if not price:
           return {
               "ticker": ticker,
               "price": None,
               "error": "price unavailable"
           }

       return {
           "ticker": ticker,
           "price": price,
           "market_cap": info.get("marketCap"),
           "pe": info.get("trailingPE"),
           "sector": info.get("sector"),
           "source": "yfinance"
       }

    except Exception as e:
        print("Stock error:", e)
        return {
            "ticker": ticker,
            "price": None,
            "error": str(e)
       }

# ==================================================
# STOCK ROUTE
# ==================================================

@app.post("/stocks/analyse")
def analyse_stock(request: StockRequest, current_user: str = Depends(get_current_user)):

    data = get_stock_data(request.ticker)

    if not data:
        raise HTTPException(status_code=400, detail="Données indisponibles")

    return data
        

# ==================================================
# PORTFOLIO
# ==================================================

@app.post("/portfolio/add")
def add_asset(request: PortfolioRequest, current_user: str = Depends(get_current_user)):

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    asset = normalize_ticker(request.asset)
    asset_type = request.asset_type.upper()

    data = get_stock_data(asset)  # ✅ DIRECT
    

    with engine.begin() as conn:

        try:
            # =========================
            # UPSERT (ANTI-DOUBLON SQL)
            # =========================
            conn.execute(text("""
                INSERT INTO portfolios (user_email, asset, asset_type, quantity, buy_price)
                VALUES (:email, :asset, :asset_type, :quantity, :buy_price)
                ON CONFLICT (user_email, asset)
                DO UPDATE SET
                    quantity = portfolios.quantity + EXCLUDED.quantity,
                    buy_price = (
                        (portfolios.quantity * portfolios.buy_price) +
                        (EXCLUDED.quantity * EXCLUDED.buy_price)
                    ) / (portfolios.quantity + EXCLUDED.quantity)
            """), {
                "email": current_user,
                "asset": asset,
                "asset_type": asset_type,
                "quantity": request.quantity,
                "buy_price": request.buy_price
            })

            return {"status": "actif ajouté ou mis à jour"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    try:
        asset = data["ticker"]

        # 🔥 UPSERT (anti doublon intelligent)
        db.execute(text("""
            INSERT INTO portfolios (user_email, asset, asset_type, quantity, buy_price)
            VALUES (:email, :asset, :asset_type, :quantity, :buy_price)
            ON CONFLICT (user_email, asset)
            DO UPDATE SET
                quantity = portfolios.quantity + EXCLUDED.quantity,
                buy_price = (
                    (portfolios.quantity * portfolios.buy_price) +
                    (EXCLUDED.quantity * EXCLUDED.buy_price)
                ) / (portfolios.quantity + EXCLUDED.quantity)
        """), {
            "email": user,
            "asset": asset,
            "asset_type": data.asset_type,
            "quantity": data.quantity,
            "buy_price": data.buy_price
        })

        # 🧹 Nettoyage sécurité (double protection)
        db.execute(text("""
            DELETE FROM portfolios a
            USING portfolios b
            WHERE a.ctid < b.ctid
            AND a.user_email = b.user_email
            AND a.asset = b.asset;
        """))

        db.commit()

        return {"status": "actif ajouté ou mis à jour"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portfolio")
def get_portfolio(current_user: str = Depends(get_current_user)):

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios
            WHERE user_email=:email
        """), {"email": current_user})

        rows = result.fetchall()

    portfolio = []
    total_value = 0
    total_cost = 0

    for r in rows:
        asset = r[0]
        asset_type = r[1]
        quantity = r[2]
        buy_price = r[3]

        ticker = normalize_ticker(asset)
        data = get_stock_data(ticker)

        # 🔥 TON BLOC (BON ENDROIT)
        if not data or not data.get("price"):
            current_price = None
            value = 0
            performance = 0
            status = "invalid"
        else:
            current_price = data["price"]
            value = quantity * current_price
            performance = ((current_price - buy_price) / buy_price) * 100
            status = "ok"

        cost = quantity * buy_price

        total_value += value
        total_cost += cost

        portfolio.append({
            "asset": asset,
            "type": asset_type,
            "quantity": quantity,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": round(value, 2),
            "performance": round(performance, 2),
            "status": status
        })

    total_performance = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

    return {
        "portfolio": portfolio,
        "summary": {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_performance": round(total_performance, 2)
        }
    }

# ==================================================
# PORTFOLIO ANALYSE
# ==================================================

@app.post("/portfolio/analyse")
def analyse_portfolio(current_user: str = Depends(get_current_user)):

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    # =========================
    # 1. GET USER PORTFOLIO
    # =========================
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios
            WHERE user_email=:email
        """), {"email": current_user})

        portfolio = [
            {
                "asset": r[0],
                "type": r[1],
                "quantity": r[2],
                "buy_price": r[3]
            } for r in result.fetchall()
        ]

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio vide")

    # =========================
    # 2. CALCUL ANALYSE
    # =========================
    total_value = 0
    asset_distribution = {}

    for asset in portfolio:
        value = asset["quantity"] * asset["buy_price"]
        total_value += value

        asset_type = asset["type"].lower()
        asset_distribution[asset_type] = asset_distribution.get(asset_type, 0) + value

    diversification = len(asset_distribution)

    analysis = {
        "total_value": total_value,
        "diversification_score": diversification,
        "distribution": asset_distribution
    }

    # =========================
    # 3. IA ADVICE (CORRIGÉ)
    # =========================
    prompt = f"""
    Tu es un expert en : 
    - gestion de patrimoine
    - family office
    - marchés financiers
    - bourse
    - trading
    - finance centralisée et décentralisée
    - investissement 
    - private equity
    - crownfunding
    - financement bancaire
    - financement participatif
    - cryptomonnaies
    - création, développement et reprise d'entreprise
    - entreprise et business physique
    - entreprise et business en ligne
    - développemet web et réseaux sociaux
    - création de richesse
    - liberté financière

     Tu aides des entrepreneurs, mais aussi des salariés, des personnes novices, à atteindre la liberté financière.

    Analyse ce portefeuille comme un conseiller financier haut de gamme.

    Données :
    - Valeur totale : {total_value}
    - Diversification : {diversification}
    - Répartition : {asset_distribution}

    Objectif : maximiser rendement + réduire risque.

    Donne une réponse structurée :

    1. Analyse globale (niveau du portefeuille)
    2. Forces (bullet points)
    3. Faiblesses / risques (bullet points)
    4. Recommandations concrètes (actions précises à faire)
    5. Stratégie idéale (court / moyen / long terme)

    Style :
    - professionnel
    - direct
    - sans blabla inutile
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        advice = response.choices[0].message.content

    except Exception as e:
        advice = f"IA indisponible: {str(e)}"

    # =========================
    # 4. RETURN
    # =========================
    return {
        "analysis": analysis,
        "ai_advice": advice
    }
# ==================================================
# IA
# ==================================================

@app.post("/ia/brain")
def brain(data: BrainRequest, user: str = Depends(get_current_user)):

    # GET PROFILE
    with engine.connect() as conn:
        result = conn.execute(text("""
        SELECT * FROM user_profiles WHERE user_email=:email
    """), {"email": current_user})

    profile = result.fetchone()

    profile_data = dict(profile._mapping) if profile else {}
    
    system_prompt = """
Tu es un conseiller en gestion de patrimoine et en family office et tu es un expert en :
- gestion de patrimoine
- family office
- marchés financiers
- bourse & trading
- crypto & DeFi
- private equity & financement
- business (online & offline)
- création de richesse
- liberté financière

Tu raisonnes comme :
- un investisseur expérimenté
- un entrepreneur pragmatique
- un stratège orienté résultats

Tu raisonnes comme :
- un investisseur expérimenté
- un entrepreneur pragmatique
- un stratège orienté résultats

Tu donnes UNIQUEMENT :
- des réponses concrètes
- des stratégies concrètes et applicables immédiatement
- des conseils réalistes et réalisables
- des réponses directes (courtes et claires)
- des explications simples (logiques + pédagogies)
- des plans d’action concrets (étapes numérotées)
- des exemples réels ou réalistes

Tu évites :
- le blabla
- les généralités
- les réponses vagues
- les disclaimers inutiles
"""
    # ✅ CONTEXTE UTILISATEUR (déclaré ici)
    user_context = f"""
    PROFIL UTILISATEUR :
    {profile_data}

    PORTEFEUILLE :
    - Valeur totale : {total_value}
    - Diversification : {diversification}
    - Répartition : {asset_distribution}

    OBJECTIF :
    Optimiser patrimoine + réduire risque + accélérer liberté financière
    
    user_prompt = f"""
Question :
{data.question}

Donne une réponse structurée STRICTEMENT comme ceci :

1. Réponse directe (max 3 phrases)
2. Explication simple (logique + pédagogique)
3. Plan d’action (étapes numérotées concrètes)
4. Exemple réel ou concret

Objectif :
→ que l’utilisateur puisse agir immédiatement
→ aider l’utilisateur à construire un patrimoine solide et atteindre la liberté financière.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,  # 🔥 important pour qualité
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_context},
                {"role": "user", "content": user_prompt}
            ]
        )

        return {
            "question": data.question,
            "answer": response.choices[0].message.content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():
    return {"status": "API active", "version": "10.1"}















