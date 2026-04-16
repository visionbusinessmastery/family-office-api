from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException, Request
from .schemas import CryptoQuery
from .service import get_crypto_intelligence

router = APIRouter()

@router.post("/crypto")
@limiter.limit("20/minute")
def crypto(request: Request, data: CryptoQuery):
    return get_crypto_intelligence(data.query)
