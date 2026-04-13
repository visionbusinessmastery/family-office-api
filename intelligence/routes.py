from fastapi import APIRouter
from .schemas import GlobalQuery
from .service import get_global_intelligence

router = APIRouter()

@router.post("/global")
def global_intelligence(query: GlobalQuery):
    return get_global_intelligence(query)
