from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from datetime import timedelta
from typing import Optional
from sqlalchemy import create_engine, text
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from openai import OpenAI
import requests
import os
import time
import yfinance as yf

# ==================================================
# CONFIG
# ==================================================

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# FIX Render Postgres
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

app = FastAPI(title="Family Office AI", version="10.0")

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
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS password TEXT
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
# AUTH FUNCTIONS
# ==================================================

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

def create_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# ==================================================
# GET CURRENT USER
# ==================================================

def get_current_user(token: str = Depends(oauth2_scheme)):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=401,
                detail="Token invalide"
            )

        return email

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Token invalide"
        )


# ==================================================
# LOGIN
# ==================================================

@app.post("/login")

def login(form_data: OAuth2PasswordRequestForm = Depends()):

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    email = form_data.username.lower()

    with engine.connect() as conn:

        result = conn.execute(text("""
            SELECT password FROM users WHERE email=:email
        """), {"email": email})

        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Identifiants invalides")

        if not verify_password(form_data.password, row[0]):
            raise HTTPException(status_code=400, detail="Mot de passe incorrect")

        token = create_token({"sub": email})

        return {
            "access_token": token,
            "token_type": "bearer"
        }

@app.get("/dev/token")

def get_test_token():
    token = create_token({"sub": "test@gmail.com"})
    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/me")

def me(user: str = Depends(get_current_user)):
    return {"user": user}


# ======================
# REGISTER
# ======================

@app.post("/register")

def register(user: UserRegister):

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    email = user.email.lower()
    hashed_password = hash_password(user.password)

    with engine.begin() as conn:

        result = conn.execute(text("""
            SELECT email FROM users WHERE email=:email
        """), {"email": email})

        if result.fetchone():
            raise HTTPException(status_code=400, detail="Utilisateur déjà existant")

        conn.execute(text("""
            INSERT INTO users (email, password)
            VALUES (:email, :password)
        """), {
            "email": email,
            "password": hashed_password
        })

    return {"status": "Utilisateur créé"}
           


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
# TICKER RESOLVER
# ==================================================

def resolve_ticker(query: str):
    query = query.strip().upper()

    # Si déjà ticker
    if len(query) <= 5 and " " not in query:
        return query

    # Recherche FMP
    url = f"https://financialmodelingprep.com/api/v3/search?query={query}&limit=1&apikey={FMP_API_KEY}"
    data = get_cached(url)

    if data and len(data) > 0:
        return data[0]["symbol"]

    return None


# ==================================================
# STOCK ANALYSE API
# ==================================================

@app.post("/stocks/analyse")

def analyse_stock(ticker: str, user=Depends(get_current_user)):

    resolved_ticker = resolve_ticker(ticker)

    if not resolved_ticker:
        raise HTTPException(status_code=404, detail="Entreprise introuvable")

    data = get_stock_data(resolved_ticker)

    if not data:
        raise HTTPException(status_code=404, detail="Données indisponibles")

    try:
        ai_result = ai_analyse_stock(data)
    except Exception as e:
        ai_result = fallback_analysis(data)

    return {
        "input": ticker,
        "ticker": resolved_ticker,
        "name": data.get("company"),
        "data": data,
        "analysis": ai_result
    }


# ==================================================
# SCORE
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


# ==================================================
# STOCK DATA (UNIQUE VERSION)
# ==================================================

def get_stock_data(ticker):

    ticker = ticker.upper()

    if not ALPHA_VANTAGE_API_KEY or not FMP_API_KEY:
        raise HTTPException(status_code=500, detail="API Keys manquantes")

    # Alpha Vantage
    alpha_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
    alpha_data = get_cached(alpha_url)
    alpha_quote = alpha_data.get("Global Quote", {}) if alpha_data else {}

    # FMP profile
    fmp_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
    fmp_data = get_cached(fmp_url)
    fmp_profile = fmp_data[0] if fmp_data and len(fmp_data) > 0 else {}

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
        "pe": fmp_profile.get("pe"),
        "market_cap": fmp_profile.get("mktCap"),
        "trend": "bullish" if momentum_score >= 50 else "bearish",
        "momentum_score": momentum_score,
        "rating": rating,
        "sources": ["Alpha Vantage", "FMP"]
    }


# ==================================================
# AI ANALYSIS (FIX OPENAI)
# ==================================================

def ai_analyse_stock(data):

    prompt = f"""
    Analyse cette action :

    Ticker: {data['ticker']}
    Prix: {data['price']}
    PE: {data.get('pe')}
    Market cap: {data.get('market_cap')}
    Tendance: {data.get('trend')}

    Donne :
    - Analyse simple
    - Recommandation (Acheter / Conserver / Vendre)
    - Niveau de risque
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


# ==================================================
# FALLBACK
# ==================================================

def fallback_analysis(data):
    if data.get("trend") == "bullish":
        return "Tendance haussière, potentiel intéressant."
    else:
        return "Marché incertain, prudence recommandée."

# ==================================================
# PORTFOLIO ANALYSIS
# ==================================================

def analyse_portfolio(email):

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    with engine.connect() as conn:

        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios
            WHERE user_email = :email
        """), {"email": email})

        rows = result.fetchall()

    if not rows:
        return None

    portfolio = []

    total_value = 0
    total_cost = 0

    allocation = {}

    for r in rows:

        asset = r[0]
        asset_type = r[1]
        quantity = r[2]
        buy_price = r[3]

        data = get_stock_data(asset)
        market_price = data["price"]

        if asset_type == "stock":

            data = get_stock_data(asset)

            if data:
                market_price = data["price"]

        value = quantity * market_price
        cost = quantity * buy_price

        total_value += value
        total_cost += cost

        allocation[asset_type] = allocation.get(asset_type, 0) + value

        portfolio.append({
            "asset": asset,
            "type": asset_type,
            "quantity": quantity,
            "buy_price": buy_price,
            "market_price": market_price,
            "value": round(value,2)
        })

    performance = total_value - total_cost

    allocation_percent = {}

    for k, v in allocation.items():
        allocation_percent[k] = round((v/total_value)*100, 2) if total_value > 0 else 0

    diversification_score = min(len(allocation)*20,100)

    if diversification_score >= 70:
        risk = "Diversifié"
    elif diversification_score >= 40:
        risk = "Modéré"
    else:
        risk = "Concentré"

    return {

        "email": email,

        "portfolio_value": round(total_value,2),

        "portfolio_cost": round(total_cost,2),

        "performance": round(performance,2),

        "diversification_score": diversification_score,

        "risk_profile": risk,

        "allocation": allocation_percent,

        "assets": portfolio

    }

@app.post("/stocks/analyse")

def analyse_stock(data: dict, user: str = Depends(get_current_user)):

    ticker = data.get("ticker")

    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker manquant")

    try:

        stock = yf.Ticker(ticker)
        info = stock.info

        if not info:
            raise HTTPException(status_code=400, detail="Données indisponibles")

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        market_cap = info.get("marketCap")
        pe = info.get("trailingPE")
        sector = info.get("sector")

        return {
            "ticker": ticker,
            "price": price,
            "market_cap": market_cap,
            "pe_ratio": pe,
            "sector": sector
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur analyse: {str(e)}")



# ==================================================
# PORTFOLIO OPTIMIZER
# ==================================================

def optimize_portfolio(email):

    data = analyse_portfolio(email)

    if not data:
        return None

    allocation = data["allocation"]

    # allocation cible simple (robo advisor basique)
    target = {
        "stock": 60,
        "crypto": 10,
        "etf": 20,
        "cash": 10
    }

    adjustments = []

    for asset in target:

        current = allocation.get(asset, 0)
        target_weight = target[asset]

        diff = round(target_weight - current, 2)

        if abs(diff) > 5:

            if diff > 0:
                action = "Augmenter"
            else:
                action = "Réduire"

            adjustments.append({
                "asset_type": asset,
                "current": current,
                "target": target_weight,
                "action": action,
                "difference_percent": diff
            })

    return {

        "email": email,

        "current_allocation": allocation,

        "target_allocation": target,

        "recommendations": adjustments,

        "message": "Optimisation basée sur un modèle robo-advisor simple"

    }


# ==================================================
# ROUTES
# ==================================================

@app.get("/")
def root():
    return {"status": "API active", "version": "10.0"}


    
# ==================================================
# PORTFOLIO
# ==================================================

@app.post("/portfolio/add")

def add_asset(request: PortfolioRequest, current_user: str = Depends(get_current_user)):
    # current_user contient l'email de l'utilisateur authentifié

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    try:
        
        with engine.begin() as conn:

            conn.execute(text("""
                INSERT INTO portfolios (user_email, asset, asset_type, quantity, buy_price)
                VALUES (:email, :asset, :asset_type, :quantity, :buy_price)
                SELECT * FROM portfolios 
                WHERE user_email=:email AND asset=:asset
            """), {
                "email": current_user,
                "asset": request.asset,
                "asset_type": request.asset_type,
                "quantity": request.quantity,
                "buy_price": request.buy_price
            })

        return {"status": "actif ajouté", "asset": request.asset}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

   
@app.get("/portfolio")

def get_portfolio(current_user: str = Depends(get_current_user)):

    if not engine:
        raise HTTPException(status_code=500, detail="Database non connectée")

    try:

        with engine.connect() as conn:

            result = conn.execute(text("""
                SELECT asset, asset_type, quantity, buy_price
                FROM portfolios
                WHERE user_email = :email
            """), {"email": current_user})

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
                "email": current_user,
                "portfolio": portfolio
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/portfolio/analyse")

def portfolio_analysis(current_user: str = Depends(get_current_user)):

    result = analyse_portfolio(current_user)

    if not result:
        raise HTTPException(status_code=404, detail="Portefeuille vide")

    return result
    

@app.get("/portfolio/optimize")

def portfolio_optimize(current_user: str = Depends(get_current_user)):

    result = optimize_portfolio(current_user)

    if not result:
        raise HTTPException(status_code=404, detail="Portefeuille vide")

    return result

   

# ==================================================
# STOCK ANALYSE
# ==================================================

@app.post("/stocks/analyse")
def analyse_stock(request: StockRequest, current_user: str = Depends(get_current_user)):
    return get_stock_data(request.ticker)
    
    if not ALPHA_VANTAGE_API_KEY or not FMP_API_KEY:
        raise HTTPException(status_code=500, detail="API Key manquante")

    data = get_stock_data(request.ticker)

    if not data:
        raise HTTPException(status_code=400, detail="Données indisponibles")

    return data

# ==================================================
# AI BRAIN
# ==================================================

@app.post("/ia/brain")
def brain(data: dict, user: str = Depends(get_current_user)):

    question = data.get("question")

    if not question:
        raise HTTPException(status_code=400, detail="Question manquante")

    try:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Tu es un expert mondial avec une apporhce globale. Tu es un conseiller financier expert en gestion de patrimoine et family office. Tu es aussi un expert en investissement immoblier, patrimonial, locatif, ou encore en achat revente. Tu es aussi un expert en création, développement et reprise d'entreprise, que se soit un business physique, ou encore un business en ligne. Tu es un expert en développement d'activité en ligne, sur internet, en application mobile ou en Saas. Tu es aussi un expert en investissement boursier, actions, etf, obligations, cryptomonnaies, devises, matières premières, marchés européens, américains, pays émergents et autres monde, et tu matrîse aussi le private equity. Tu parles aux utilisateurs comme un amis qui souhaite aider, former et accompagner les utilisateurs. Tu utilise des termes techniques, mais penses à expliquer de manière simple les termes techniques, car tu parles à des gens qui sont des novices. donne des conseils et astuces réalistes et concrets en tenant compte de la situation de l'utilisateur. donne aux moins 5 et 10 maximum actions à entreprendre, à acheter, à mettre en oeuvre avec un planning et des exercices pratiques. Tu dois aider l'utilisateur et l'inciter à passer à l'action   ."
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        )

        answer = response.choices[0].message.content

        return {
            "question": question,
            "answer": answer
        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=f"Erreur IA: {str(e)}")
        
def ask_ai(user, question):
    portfolio = get_user_portfolio(user)

    prompt = f"""
    Tu es un expert en gestion de patrimoine, en immobilier, en investissement boursier et private equity, en création, développement et reprise d'entreprise physique ou en ligne.

    Données utilisateur :
    {portfolio}

    Question :
    {question}

    Donne une réponse personnalisée avec recommandations concrètes.
    """

    return call_openai(prompt)
    
def ask_ai(question):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question}]
        )
        return response.choices[0].message.content

    except Exception as e:
        return "L'IA est temporairement indisponible. Réessaie plus tard."

def fallback_response(question):
    if "patrimoine" in question.lower():
        return "Pour développer ton patrimoine : investir en bourse, immobilier, et diversifier tes revenus."
    
    return "Service IA temporairement indisponible."

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

@app.get("/test-db")
def test_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return {"db": "ok"}


@app.get("/test-users")
def test_users():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users LIMIT 1"))
        return {"status": "table users ok"}

@app.get("/schema")
def schema():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='users'
        """))
        return [row[0] for row in result]




























