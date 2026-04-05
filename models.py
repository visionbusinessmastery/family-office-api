from sqlalchemy import Column, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

class Portfolio(BaseModel):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True)
    asset = Column(String)
    asset_type = Column(String)
    quantity = Column(Integer)
    buy_price = Column(Float)
