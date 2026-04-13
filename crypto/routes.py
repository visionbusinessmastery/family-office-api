from fastapi import APIRouter
from .schemas import CryptoQuery
from .service import get_crypto_intelligence

router = APIRouter()

@router.post("/crypto")
def crypto(query: CryptoQuery):
    return get_crypto_intelligence(query)
