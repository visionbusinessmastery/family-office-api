from sqlalchemy import text
from database import engine

def get_user_portfolio(email):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolios WHERE user_email=:email
        """), {"email": email})

        return result.fetchall()
