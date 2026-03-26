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

# ==================================================
# STOCK DATA
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


def get_stock_data(ticker: str):

    ticker = ticker.upper()

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
            return None

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
        return None

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

    asset = request.asset.upper()
    asset_type = request.asset_type.upper()

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
        asset = data.asset.upper()

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

        return {
            "portfolio": [
                {
                    "asset": r[0],
                    "type": r[1],
                    "quantity": r[2],
                    "buy_price": r[3]
                } for r in result.fetchall()
            ]
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
    Analyse ce portefeuille :

    Valeur totale : {total_value}
    Diversification : {diversification}
    Répartition : {asset_distribution}

    Donne :
    - Forces
    - Risques
    - Recommandations concrètes
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

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": data.question}]
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

# ==================================================
# FIX DATA BASE A ENLEVER PAR LA SUITE
# ==================================================

@app.get("/fix-db")
def fix_db():
    if not engine:
        return {"error": "no db"}

    with engine.begin() as conn:

        # 🔍 voir les doublons
        duplicates = conn.execute(text("""
        SELECT user_email, asset, COUNT(*)
        FROM portfolios
        GROUP BY user_email, asset
        HAVING COUNT(*) > 1;
        """)).fetchall()

        print("DOUBLONS:", duplicates)

        # 🧨 supprimer TOUTES les lignes en double (on garde 1 seule)
        conn.execute(text("""
        DELETE FROM portfolios
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM portfolios
            GROUP BY user_email, asset
        );
        """))

        # 🔥 supprimer ancienne contrainte si elle existe
        conn.execute(text("""
        ALTER TABLE portfolios
        DROP CONSTRAINT IF EXISTS unique_user_asset;
        """))

        # 🧱 recréer contrainte propre
        conn.execute(text("""
        ALTER TABLE portfolios
        ADD CONSTRAINT unique_user_asset UNIQUE (user_email, asset);
        """))

    return {"status": "database fixed clean"}

















