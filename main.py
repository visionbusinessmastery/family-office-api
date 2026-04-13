from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from auth.routes import router as auth_router
from stocks.routes import router as stocks_router
from portfolio.routes import router as portfolio_router
from market.routes import router as market_router
from real_estate.routes import router as real_router
from business.routes import router as business_router
from ai.routes import router as ai_router
from crm.routes import router as crm_router

app = FastAPI(title="Family Office AI", version="10.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ROUTERS
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(stocks_router, prefix="/stocks", tags=["Stocks"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(market_router, prefix="/market", tags=["Market"])
app.include_router(real_router, prefix="/real", tags=["Real"])
app.include_router(business_router, prefix="/business", tags=["Business"])
app.include_router(ai_router, prefix="/ai", tags=["AI"])
app.include_router(crm_router, prefix="/crm", tags=["CRM"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    
@app.get("/")
def root():
    return {"status": "API running"}












