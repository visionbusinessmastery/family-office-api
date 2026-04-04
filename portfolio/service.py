from sqlalchemy import text
from database import engine

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
            

        


