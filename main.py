from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import requests
FMP_API_KEY = os.getenv("FMP_API_KEY")

app = FastAPI(title="Family Office IA API", version="0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Autorise tous les frontends (OK pour MVP)
    allow_credentials=True,
    allow_methods=["*"],  # Autorise POST, OPTIONS, etc.
    allow_headers=["*"],
)

# ======================
# MODELS
# ======================

class IARequest(BaseModel):
    message: str

class BudgetRequest(BaseModel):
    revenus: float
    charges: float
    patrimoine: Optional[float] = 0

# ======================
# ROUTES
# ======================

@app.get("/")
def root():
    return {"status": "Family Office IA API running"}


@app.post("/ia/analyse")
def ia_analyse(request: IARequest):
    message = request.message.lower()

    if not user_profile:
        return {
            "diagnostic": "Profil utilisateur non renseigné",
            "axes": ["Merci de compléter votre profil financier"],
            "plan_action": ["Renseigner revenus, charges, objectifs"],
            "note": "Profil requis pour une analyse personnalisée"
        }

    revenus = user_profile["revenus"]
    charges = user_profile["charges"]
    objectif = user_profile["objectif"]
    horizon = user_profile["horizon"]
    risque = user_profile["risque"]

    reste = revenus - charges

    diagnostic = (
        f"Revenus mensuels : {revenus} €\n"
        f"Charges mensuelles : {charges} €\n"
        f"Capacité mensuelle : {reste} €\n"
        f"Horizon : {horizon} ans\n"
        f"Profil de risque : {risque}"
    )

    axes = []
    if reste <= 0:
        axes.append("Optimisation budgétaire prioritaire")
    else:
        axes.append("Capacité d’investissement détectée")

    axes.append(f"Objectif principal : {objectif}")

    plan_action = [
        "Structurer une épargne de sécurité (3 à 6 mois de charges)",
        "Définir une allocation d’actifs cohérente avec le risque",
        "Mettre en place une stratégie progressive et diversifiée"
    ]

    return {
        "diagnostic": diagnostic,
        "axes": axes,
        "plan_action": plan_action,
        "note": "Analyse personnalisée – aide à la décision, pas un conseil réglementé"
    }

@app.post("/budget/analyse")
def budget_analyse(request: BudgetRequest):
    reste = request.revenus - request.charges

    situation = "équilibrée"
    if reste < 0:
        situation = "déficitaire"
    elif reste > 0:
        situation = "excédentaire"

    return {
        "revenus": request.revenus,
        "charges": request.charges,
        "reste": reste,
        "situation": situation,
        "suggestion": (
            "Capacité d'investissement détectée"
            if reste > 0
            else "Optimisation budgétaire prioritaire"
        )
    }

from pydantic import BaseModel

# --- Modèle Profil ---
class ProfileRequest(BaseModel):
    revenus: float
    charges: float
    objectif: str
    horizon: int
    risque: str

# --- Stockage simple (MVP) ---
user_profile = {}

@app.post("/profile")
def save_profile(profile: ProfileRequest):
    global user_profile
    user_profile = profile.dict()

    return {
        "status": "ok",
        "message": "Profil enregistré",
        "profile": user_profile
    }
@app.post("/stocks/analyse")
def analyse_action(data: dict):

    ticker = data.get("ticker")

    if not ticker:
        return {"error": "Ticker manquant"}

    return {
        "ticker": ticker.upper(),
        "entreprise": "Entreprise simulée",
        "score": 7,
        "analyse": "Entreprise solide avec croissance stable.",
        "forces": [
            "Bonne croissance",
            "Position dominante",
            "Rentabilité solide"
        ],
        "risques": [
            "Valorisation élevée",
            "Sensibilité au marché"
        ],
        "strategie": "Accumulation progressive long terme"
    }

@app.get("/stockpicker")
def stock_picker():

    if not FMP_API_KEY:
        return {"result": "Clé API manquante"}

    url = f"https://financialmodelingprep.com/stable/stock-screener?marketCapMoreThan=10000000000&volumeMoreThan=1000000&limit=10&apikey={FMP_API_KEY}"

    try:

        response = requests.get(url)
        stocks = response.json()

        result = "📈 Actions détectées par l'IA :\n\n"

        for stock in stocks:

            result += f"""• {stock['companyName']} ({stock['symbol']})
Prix : {stock['price']} $
Secteur : {stock['sector']}

"""

        return {"result": result}

    except Exception as e:
        return {"result": f"Erreur récupération données marché : {str(e)}"}
        
# ======================
# FUTURES EXTENSIONS
# ======================
# - Authentification JWT
# - Connexion Open Banking (Revolut)
# - IA Coach avancé
# - Stockage base de données






