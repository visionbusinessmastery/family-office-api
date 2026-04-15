from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter
from .schemas import LeadRequest
from .odoo import OdooClient

router = APIRouter()
odoo = OdooClient()

@router.post("/lead")
@limiter.limit("10/minute")
def create_lead(request: Request, data: RegisterRequest):
def create_lead(data: LeadRequest):

    def _create_lead():
        contact_id = odoo.create_contact(data.name, data.email)
        return {"contact_id": contact_id}

    return safe_execute(_create_lead, module_name="CRM")


