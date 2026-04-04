from fastapi import APIRouter
from crm.odoo import OdooClient

router = APIRouter()
odoo = OdooClient()

@router.post("/lead")
def create_lead(name: str, email: str):
    contact_id = odoo.create_contact(name, email)
    return {"contact_id": contact_id}
