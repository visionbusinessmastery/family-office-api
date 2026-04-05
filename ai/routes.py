from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user
from openai import OpenAI
from .schemas import BrainRequest
import os

router = APIRouter()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/ia/brain")
def brain(data: BrainRequest, user: str = Depends(get_current_user)):

    # ======================
    # PROFILE
    # ======================
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM user_profiles WHERE user_email=:email
        """), {"email": user})

        profile = result.fetchone()

    profile_data = dict(profile._mapping) if profile else {}

    # ======================
    # PORTFOLIO
    # ======================
    portfolio_data = []
    total_value = 0

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios
            WHERE user_email=:email
        """), {"email": user})

        rows = result.fetchall()

    for r in rows:
        value = r[2] * r[3]
        total_value += value

        portfolio_data.append({
            "asset": r[0],
            "type": r[1],
            "value": value
        })

    diversification = len(set([p["type"] for p in portfolio_data]))
    asset_distribution = {}

    for p in portfolio_data:
        t = p["type"]
        asset_distribution[t] = asset_distribution.get(t, 0) + p["value"]

    # ======================
    # PROMPT
    # ======================
    system_prompt = """Tu es un expert en gestion de patrimoine et family office. Réponses concrètes uniquement."""

    user_prompt = f"""
Profil: {profile_data}
Portfolio: {portfolio_data}
Total: {total_value}

Question: {data.question}

Réponds en:
1. Réponse directe
2. Explication
3. Plan d’action
4. Exemple
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        return {
            "question": data.question,
            "answer": response.choices[0].message.content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

