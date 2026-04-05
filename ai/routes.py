from database import get_db
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict
from auth.utils import get_current_user
from ai.service import generate_advice
from .schemas import BrainRequest
import os

# ==================================================
# CONFIG AI BRAIN
# ==================================================

router = APIRouter()

# ==================================================
# AI BRAIN ANALYZE
# ==================================================
@router.post("/brain")
def brain(question: str, user: str = Depends(get_current_user)):
    prompt = f"User: {user} Question: {question}"
    answer = generate_advice(prompt)
    return {"answer": answer}

# ==================================================
# IA BRAIN PRESONNAL ADVICES
# ==================================================
@router.post("/ia/brain")
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

