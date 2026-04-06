from fastapi import APIRouter, Depends, HTTPException
from auth.utils import get_current_user
from .schemas import BrainRequest
from .service import generate_advice
from sqlalchemy import text
from database import engine
from portfolio.service import get_user_portfolio

router = APIRouter()

@router.post("/ia/brain")
def brain(data: BrainRequest, user: str = Depends(get_current_user)):

    try:
        # ======================
        # PROFILE
        # ======================
        with engine.connect() as conn:
            profile = conn.execute(text("""
                SELECT * FROM user_profiles WHERE user_email=:email
            """), {"email": user}).fetchone()

        profile_data = dict(profile._mapping) if profile else {}

        # ======================
        # PORTFOLIO
        # ======================
        portfolio_data = get_user_portfolio(user_email)
        total_value = 0
        
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT asset, asset_type, quantity, buy_price
                FROM portfolio
                WHERE user_email=:email
            """), {"email": user}).fetchall() 

        for r in rows:
            value = r[2] * r[3]
            total_value += value

            portfolio_data.append({
                "asset": r[0],
                "type": r[1],
                "value": value
            })

        # ======================
        # PROMPT
        # ======================
        prompt = f"""
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

        answer = generate_advice(prompt)

        return {
            "question": data.question,
            "answer": answer
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
