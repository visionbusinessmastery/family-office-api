from sqlalchemy import text
from database import engine
from pydantic import BaseModel, EmailStr, Field

import models

# ==================================================
# CONFIG PORTFOLIO
# ==================================================



# ==================================================
# GET USER PORTFOLIO
# ==================================================
def get_user_portfolio(email):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios WHERE user_email=:email
        """), {"email": email})

        return result.fetchall()

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
# PORTFOLIO USER ANALYSE
# ==================================================
@app.post("/portfolio/analyse/ai")
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
# PORTFOLIO USER ADD
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
            

        


