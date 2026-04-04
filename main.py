from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.routes import router as auth_router
from portfolio.routes import router as portfolio_router
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
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(ai_router, prefix="/ai", tags=["AI"])
app.include_router(crm_router, prefix="/crm", tags=["CRM"])

@app.get("/")
def root():
    return {"status": "API running"}











