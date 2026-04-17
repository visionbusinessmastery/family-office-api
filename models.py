from sqlalchemy import Column, Integer, String, Float
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)


class Portfolio(Base):
    __tablename__ = "portfolios"  # ⚠️ aligné avec tes requêtes SQL

    id = Column(Integer, primary_key=True, index=True)
    asset = Column(String)
    asset_type = Column(String)
    quantity = Column(Float)
    buy_price = Column(Float)
