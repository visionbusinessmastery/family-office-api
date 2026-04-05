from database import get_db, engine
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from .schemas import LeadRequest
from database import Base

from openai import OpenAI

import requests
import os

# ==================================================
# CONFIG ODOO
# ==================================================

router = APIRouter()

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==================================================
# CLIENT BASE ODOO
# ==================================================

class OdooClient:
    def __init__(self):
        self.url = f"{ODOO_URL}/jsonrpc"
        self.uid = self.login()

    def login(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD]
            },
            "id": 1
        }
        return requests.post(self.url, json=payload).json().get("result")

    def create_contact(self, name, email):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB, self.uid, ODOO_PASSWORD,
                    'res.partner', 'create',
                    [{"name": name, "email": email}]
                ]
            },
            "id": 2
        }
        return requests.post(self.url, json=payload).json().get("result")

# ==================================================
# CREATE LEAD ODOO
# ==================================================
@router.post("/lead")
def create_lead(data: LeadRequest):
    try:
        contact_id = odoo.create_contact(data.name, data.email)
        return {"contact_id": contact_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur Odoo")
        
    def update_contact(self, contact_id, update_fields: dict):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        ODOO_DB, self.uid, ODOO_PASSWORD,
                        'res.partner', 'write',
                        [[contact_id], update_fields]
                    ]
                },
                "id": 3
            }
            res = requests.post(self.url, json=payload).json()
            return res.get("result")
        except Exception as e:
            print(f"Erreur update contact Odoo: {e}")
            return None

    def create_opportunity(self, contact_id, title, expected_revenue):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        ODOO_DB, self.uid, ODOO_PASSWORD,
                        'crm.lead', 'create',
                        [{"name": title, "partner_id": contact_id, "planned_revenue": expected_revenue}]
                    ]
                },
                "id": 4
            }
            res = requests.post(self.url, json=payload).json()
            return res.get("result")
        except Exception as e:
            print(f"Erreur création opportunité Odoo: {e}")
            return None
            
