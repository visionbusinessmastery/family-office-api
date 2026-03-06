from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import os
import time

# ======================
# CONFIG
# ======================

API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

app = FastAPI(
    title="Family Office IA API",
    version="2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# STOCKAGE SIMPLE (MVP)
# ======================

user_profile = {}

# ======================
# MODELS
# ======================

class IARequest(BaseModel):
    message: str


class ProfileRequest(BaseModel):

    revenus: float
    charges: float

    epargne: float
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
# ROUTE TEST
# ======================

@app.get("/")
def root():
    return {"status": "Family Office IA API running"}


# ======================
# PROFIL UTILISATEUR
# ======================

@app.post("/profile")
def save_profile(profile: ProfileRequest):

    global user_profile
    user_profile = profile.dict()

    capacite = profile.revenus - profile.charges

    patrimoine_total = (
        profile.epargne +
        profile.immobilier +
        profile.investissements +
        profile.crypto
    )

    # Détermination du profil investisseur
    if profile.risque == "Prudent":
        profil_investisseur = "Défensif"
    elif profile.risque == "Modéré":
        profil_investisseur = "Équilibré"
    else:
        profil_investisseur = "Dynamique"

    return {
        "status": "ok",
        "message": "Profil enregistré",
        "profil_investisseur": profil_investisseur,
        "capacite_investissement": capacite,
        "patrimoine_total": patrimoine_total
    }


# ======================
# COACH IA
# ======================

@app.post("/ia/analyse")
def ia_analyse(request: IARequest):

    if not user_profile:
        return {
            "diagnostic": "Profil non renseigné",
            "axes": ["Compléter votre profil"],
            "plan_action": ["Enregistrer vos données financières"],
            "note": "Profil requis"
        }

    revenus = user_profile["revenus"]
    charges = user_profile["charges"]
    reste = revenus - charges

    axes = []

    if reste <= 0:
        axes.append("Optimisation budgétaire prioritaire")
    else:
        axes.append("Capacité d’investissement détectée")

    return {
        "diagnostic": f"Capacité mensuelle : {reste} €",
        "axes": axes,
        "plan_action": [
            "Constituer épargne de sécurité",
            "Investir progressivement",
            "Diversifier les actifs"
        ],
        "note": "Analyse IA d'aide à la décision"
    }


# ======================
# SCORE INTERNE
# ======================

def calculate_score(change):

    try:
        value = float(change.replace("%", ""))

        if value > 5:
            return 90
        elif value > 2:
            return 75
        elif value > 0:
            return 60
        else:
            return 40

    except:
        return 50


# ======================
# TOP GAINERS (UNE SEULE REQUÊTE)
# ======================

@app.get("/stockpicker")
def stock_picker():

    if not API_KEY:
        return {"top_stocks": []}

    try:

        url = (
            "https://www.alphavantage.co/query"
            f"?function=TOP_GAINERS_LOSERS"
            f"&apikey={API_KEY}"
        )

        r = requests.get(url)
        data = r.json()

        gainers = data.get("top_gainers", [])

        top_stocks = []

        for stock in gainers[:5]:

            score = calculate_score(stock.get("change_percentage", "0%"))

            top_stocks.append({
                "symbol": stock.get("ticker"),
                "price": stock.get("price"),
                "change": stock.get("change_percentage"),
                "score": score
            })

        return {"top_stocks": top_stocks}

    except:
        return {"top_stocks": []}


# ======================
# ANALYSE ACTION
# ======================

@app.post("/stocks/analyse")
def analyse_action(data: dict):

    ticker = data.get("ticker")

    if not ticker:
        return {"error": "Ticker manquant"}

    ticker = ticker.upper()

    if not API_KEY:
        return {"error": "Clé API manquante"}

    try:

        url = (
            "https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE"
            f"&symbol={ticker}"
            f"&apikey={API_KEY}"
        )

        r = requests.get(url)
        data_json = r.json()

        # 🔎 Vérification exacte
        if "Global Quote" not in data_json:
            return {
                "error": "Réponse API invalide",
                "debug": data_json
            }

        quote = data_json["Global Quote"]

        # Vérifier que le prix existe
        if not quote.get("05. price"):
            return {
                "error": "Données incomplètes",
                "debug": quote
            }

        return {
            "ticker": ticker,
            "prix": float(quote["05. price"]),
            "variation": quote.get("10. change percent"),
            "analyse": "Données temps réel Alpha Vantage",
            "forces": ["Prix officiel", "Mise à jour quotidienne"],
            "risques": ["Limite API gratuite"],
            "strategie": "Analyse technique et fondamentale à ajouter"
        }

    except Exception as e:
        return {"error": f"Erreur serveur: {str(e)}"}

# ======================
# IMMOBILIER
# ======================

@app.get("/realestate/opportunities")
def realestate_opportunities():

    return {
        "real_estate": [
            {"ville": "Lisbonne", "rendement": "6.5%"},
            {"ville": "Dubaï", "rendement": "7.2%"},
            {"ville": "Athènes", "rendement": "6%"}
        ]
    }


# ======================
# BUSINESS
# ======================

@app.get("/business/ideas")
def business_ideas():

    return {
        "business_ideas": [
            {"idea": "Agence IA pour PME"},
            {"idea": "Location courte durée automatisée"},
            {"idea": "Newsletter premium marchés financiers"}
        ]
    }


# ======================
# TENDANCES
# ======================

@app.get("/market/trends")
def market_trends():

    return {
        "secteurs_croissance": [
            "Intelligence artificielle",
            "Cyber sécurité",
            "Semi-conducteurs",
            "Energies renouvelables"
        ],
        "secteurs_declins": [
            "Retail physique",
            "Presse papier"
        ],
        "secteurs_emergents": [
            "Spatial",
            "Biotech longévité",
            "Robotique"
        ]
    }


