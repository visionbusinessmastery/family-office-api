from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException
from .schemas import CryptoQuery
from .service import get_crypto_intelligence

router = APIRouter()

@router.post("/crypto")
@limiter.limit("20/minute")
def crypto(query: CryptoQuery):
    return get_crypto_intelligence(query)
