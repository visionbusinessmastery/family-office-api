from fastapi import APIRouter, HTTPException
from .schemas import LeadRequest
from .odoo import OdooClient

router = APIRouter()
odoo = OdooClient()

@router.post("/lead")
def create_lead(data: LeadRequest):
    try:
        contact_id = odoo.create_contact(data.name, data.email)
        return {"contact_id": contact_id}
    except:
        raise HTTPException(status_code=500, detail="Erreur Odoo")


