from fastapi import APIRouter, Depends
from auth.routes import get_current_user
from portfolio.service import get_user_portfolio
from .schemas import StockRequest
from .schemas import PortfolioRequest
import os

# ==================================================
# CONFIG PROTFOLIO
# ==================================================

router = APIRouter()

# ==================================================
# GET PORTFOLIO
# ==================================================
@router.get("/")
def get_portfolio(user: str = Depends(get_current_user)):
    data = get_user_portfolio(user)
    return {"portfolio": [dict(r._mapping) for r in data]}      
    
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

# ==================================================
# NORMALIZE TICKER
# ==================================================

def normalize_ticker(input_value: str):
    value = input_value.lower().strip()

    # 1. vérifier si c’est un nom connu
    if value in COMPANY_TO_TICKER:
        return COMPANY_TO_TICKER[value]

    # 2. sinon considérer que c’est un ticker
    return value.upper()

# ==================================================
# ADVANCE CALCULS
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
# STOCK ANALYZE
# ==================================================
@router.post("/stocks/analyse")
def analyse_stock(request: StockRequest, current_user: str = Depends(get_current_user)):

    data = get_stock_data(request.ticker)

    if not data:
        raise HTTPException(status_code=400, detail="Données indisponibles")

    return data
    
# ==================================================
# PORTFOLIO USER ADD
# ==================================================
@router.post("/portfolio/add")
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


# ==================================================
# PORTFOLIO USER ANALYSE
# ==================================================
@router.post("/portfolio/analyse/ai")
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


  

