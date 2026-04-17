from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import LeadRequest
from .odoo import OdooClient

router = APIRouter()


# =========================
# CREATE LEAD
# =========================
@router.post("/lead")
@limiter.limit("10/minute")
def create_lead(request: Request, data: LeadRequest):

    def _create_lead():

        user_email = request.state.user_email

        odoo = OdooClient()

        contact_id = odoo.create_contact(
            name=data.name,
            email=data.email
        )

        return {
            "user": user_email,
            "contact_id": contact_id
        }

    return safe_execute(_create_lead, module_name="CRM")

