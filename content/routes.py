from fastapi import APIRouter, Request
from core.utils import safe_execute
from .schemas import ContentRequest
from .service import generate_business_content, generate_real_estate_content
from .schemas import PersonalizedContentRequest
from .service import generate_personalized_content

router = APIRouter()

# =========================
# BUSINESS
# =========================
@router.post("/content/business")
def business_content(request: Request, data: ContentRequest):

    def _business():
        user_email = request.state.user_email

        result = generate_business_content(
            data.budget,
            data.risk,
            data.goal
        )

        return {
            "user": user_email,
            "type": "business",
            "input": data.dict(),
            "content": result
        }

    return safe_execute(_business, module_name="CONTENT_BUSINESS")


# =========================
# REAL ESTATE
# =========================
@router.post("/content/real-estate")
def real_estate_content(request: Request, data: ContentRequest):

    def _real_estate():
        user_email = request.state.user_email

        result = generate_real_estate_content(
            data.budget,
            data.risk,
            data.goal
        )

        return {
            "user": user_email,
            "type": "real_estate",
            "input": data.dict(),
            "content": result
        }

    return safe_execute(_real_estate, module_name="CONTENT_REAL_ESTATE")
    

# =========================
# PERSONALIZED CONTENT
# =========================
@router.post("/content/personalized")
def personalized_content(request: Request, data: PersonalizedContentRequest):

    def _personalized():
        user_email = request.state.user_email

        result = generate_personalized_content(
            user_email,
            data.goal
        )

        return {
            "user": user_email,
            "type": "personalized",
            "goal": data.goal,
            "content": result
        }

    return safe_execute(_personalized, module_name="CONTENT_PERSONALIZED")
