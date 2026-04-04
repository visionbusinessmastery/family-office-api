from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict
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
from database import SessionLocal

# ==================================================
# CONFIG
# ==================================================

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")

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

class UserProfileRequest(BaseModel):
    genre: Optional[str] = None
    age: Optional[int] = None

    situation_pro: Optional[str] = None
    revenus_mensuels: Optional[float] = 0
    revenus_annuels: Optional[float] = 0

    situation_familiale: Optional[str] = None
    enfants: Optional[bool] = False
    nb_enfants: Optional[int] = 0

    logement: Optional[str] = None
    valeur_bien: Optional[float] = 0
    prix_achat: Optional[float] = 0

    dettes: Optional[dict] = {}
    epargne: Optional[dict] = {}
    investissements: Optional[dict] = {}

class OdooClient:
    def __init__(self):
        self.url = f"{ODOO_URL}/jsonrpc"
        self.uid = None
        self.login()

class UserProfile(BaseModel):
    genre: Optional[str] = None
    age: Optional[int] = None
    situation_pro: Optional[str] = None
    revenus_mensuels: Optional[float] = None
    revenus_annuels: Optional[float] = None
    situation_familiale: Optional[str] = None
    enfants: Optional[bool] = None
    nb_enfants: Optional[int] = None
    logement: Optional[str] = None
    valeur_bien: Optional[float] = None
    prix_achat: Optional[float] = None
    dettes: Optional[Dict] = {}
    epargne: Optional[Dict] = {}
    investissements: Optional[Dict] = {}
    
class PortfolioAnalysis(BaseModel):
    total_value: float
    diversification_score: float
    ai_advice: str
    premium: bool = False  # Si premium, créer opportunité CRM

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

                genre TEXT,
                age INTEGER,

                situation_pro TEXT,
                revenus_mensuels FLOAT,
                revenus_annuels FLOAT,

                situation_familiale TEXT,
                enfants BOOLEAN,
                nb_enfants INTEGER,

                logement TEXT,
                valeur_bien FLOAT,
                prix_achat FLOAT,

                dettes JSON,
                epargne JSON,
                investissements JSON,

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
# ODOO
# ==================================================
ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

class OdooClient:
    def __init__(self):
        self.url = f"{ODOO_URL}/jsonrpc"
        self.uid = None
        self.login()

    def login(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]
            },
            "id": 1
        }
        res = requests.post(self.url, json=payload).json()
        self.uid = res.get("result")
        if not self.uid:
            raise Exception("Impossible de se connecter à Odoo")
        return self.uid

    def create_contact(self, name, email):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        ODOO_DB, self.uid, ODOO_PASSWORD,
                        'res.partner', 'create',
                        [{"name": name, "email": email}]
                    ]
                },
                "id": 2
            }
            res = requests.post(self.url, json=payload).json()
            return res.get("result")
        except Exception as e:
            print(f"Erreur création contact Odoo: {e}")
            return None

    def update_contact(self, contact_id, update_fields: dict):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        ODOO_DB, self.uid, ODOO_PASSWORD,
                        'res.partner', 'write',
                        [[contact_id], update_fields]
                    ]
                },
                "id": 3
            }
            res = requests.post(self.url, json=payload).json()
            return res.get("result")
        except Exception as e:
            print(f"Erreur update contact Odoo: {e}")
            return None

    def create_opportunity(self, contact_id, title, expected_revenue):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        ODOO_DB, self.uid, ODOO_PASSWORD,
                        'crm.lead', 'create',
                        [{"name": title, "partner_id": contact_id, "planned_revenue": expected_revenue}]
                    ]
                },
                "id": 4
            }
            res = requests.post(self.url, json=payload).json()
            return res.get("result")
        except Exception as e:
            print(f"Erreur création opportunité Odoo: {e}")
            return None
            
# --- Endpoints ---
@app.post("/register")
def register_user(profile: dict):
    # 1️⃣ Vérifie si l’utilisateur existe déjà dans ton DB SaaS
    user_exists = False # À remplacer par ta logique DB
    if user_exists:
        raise HTTPException(status_code=400, detail="User already exists")

    # 2️⃣ Crée contact Odoo
    odoo_contact_id = odoo.create_contact(profile.name, profile.email)
    if not odoo_contact_id:
        print("Erreur Odoo: contact non créé")

    # 3️⃣ Retourne statut
    return {"status": "ok", "odoo_contact_id": odoo_contact_id}

@app.post("/profile/save")
def save_profile(profile: UserProfile):
    # 1️⃣ Update ton DB SaaS ici
    contact_id = 1  # Récupère depuis DB le contact Odoo correspondant
    update_fields = {"name": profile.name, "email": profile.email}
    odoo.update_contact(contact_id, update_fields)
    return {"status": "ok"}

@app.post("/portfolio/analyse")
def portfolio_analyse(analysis: PortfolioAnalysis):
    # 1️⃣ Analyse portfeuille dans ton DB SaaS
    print("Analyse :", analysis.ai_advice)

    # 2️⃣ Si premium, créer opportunité CRM
    if analysis.premium:
        contact_id = 1  # récupère contact Odoo
        opportunity_title = "Portefeuille Premium à analyser"
        expected_revenue = analysis.total_value
        odoo.create_opportunity(contact_id, opportunity_title, expected_revenue)

    return {"status": "ok", "advice": analysis.ai_advice}

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

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):

    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT email, password FROM users WHERE email=:email
        """), {"email": form_data.username}).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not verify_password(form_data.password, user[1]):
        raise HTTPException(status_code=401, detail="Wrong password")

    access_token = create_token({"sub": user[0]})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/register")
def register(user: UserRegister):

    hashed_password = hash_password(user.password)

    with engine.begin() as conn:
        try:
            conn.execute(text("""
                INSERT INTO users (email, password)
                VALUES (:email, :password)
            """), {
                "email": user.email,
                "password": hashed_password
            })
        except:
            raise HTTPException(status_code=400, detail="User already exists")

    return {"status": "user created"}
    
@app.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}

@app.post("/profile/save")
def save_profile(data: UserProfileRequest, user: str = Depends(get_current_user)):

    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO user_profiles (
            user_email, genre, age, situation_pro,
            revenus_mensuels, revenus_annuels,
            situation_familiale, enfants, nb_enfants,
            logement, valeur_bien, prix_achat,
            dettes, epargne, investissements
        )
        VALUES (
            :email, :genre, :age, :situation_pro,
            :revenus_mensuels, :revenus_annuels,
            :situation_familiale, :enfants, :nb_enfants,
            :logement, :valeur_bien, :prix_achat,
            :dettes, :epargne, :investissements
        )
        ON CONFLICT (user_email)
        DO UPDATE SET
            genre = EXCLUDED.genre,
            age = EXCLUDED.age,
            situation_pro = EXCLUDED.situation_pro,
            revenus_mensuels = EXCLUDED.revenus_mensuels,
            revenus_annuels = EXCLUDED.revenus_annuels,
            situation_familiale = EXCLUDED.situation_familiale,
            enfants = EXCLUDED.enfants,
            nb_enfants = EXCLUDED.nb_enfants,
            logement = EXCLUDED.logement,
            valeur_bien = EXCLUDED.valeur_bien,
            prix_achat = EXCLUDED.prix_achat,
            dettes = EXCLUDED.dettes,
            epargne = EXCLUDED.epargne,
            investissements = EXCLUDED.investissements,
            updated_at = CURRENT_TIMESTAMP
        """), {
            "email": user,
            **data.dict()
        })

    return {"status": "profil sauvegardé"}
    

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
    """), {"email": user})

    profile = result.fetchone()
    profile_data = dict(profile._mapping) if profile else {}

    # ⚠️ fallback valeurs (évite crash)
    total_value = 0
    diversification = 0
    asset_distribution = {}

    # GET PORTFOLIO DATA
    portfolio_data = []
    total_value = 0

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios
            WHERE user_email=:email
        """), {"email": user})

        for r in result.fetchall():
            value = r[2] * r[3]
            total_value += value

        portfolio_data.append({
            "asset": r[0],
            "type": r[1],
            "value": value
        })
        
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

Tu donnes UNIQUEMENT :
- des réponses concrètes
- des stratégies concrètes et applicables immédiatement
- des conseils réalistes et réalisables
- des réponses directes (courtes et claires)
- des explications simples (logiques + pédagogies)
- des plans d'action concrets (etapes numerotees)
- des exemples reels ou realistes

Tu evites :
- le blabla
- les generalites
- les reponses vagues
"""

    user_context = f"""
PROFIL UTILISATEUR :
{profile_data}
PORTEFEUILLE DETAILLE :
{portfolio_data}

PORTEFEUILLE :
- Valeur totale : {total_value}
- Diversification : {diversification}
- Repartition : {asset_distribution}

OBJECTIF :
Optimiser patrimoine + reduire risque + accelerer liberte financiere
"""

    user_prompt = f"""
Question :
{data.question}

Donne une reponse structuree STRICTEMENT comme ceci :

1. Reponse directe (max 3 phrases)
2. Explication simple (logique + pedagogique)
3. Plan d'action (etapes numerotees concretes)
4. Exemple reel ou concret

Objectif :
→ que l’utilisateur puisse agir immediatement
→ aider l’utilisateur a construire un patrimoine solide et atteindre la liberte financiere.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
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















