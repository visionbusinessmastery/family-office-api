from database import get_db, engine
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict

from crm.odoo import OdooClient
from .schemas import UserProfile
from portfolio.schemas import PortfolioAnalysis

import os

# ==================================================
# CONFIG ODOO
# ==================================================

router = APIRouter()
odoo = OdooClient()

# ==================================================
# ODOO REGSITER
# ==================================================
@router.post("/odoo/register")
def register_user(profile: dict):
    # 1️⃣ Vérifie si l’utilisateur existe déjà dans ton DB SaaS
    user_exists = False # À remplacer par ta logique DB
    if user_exists:
        raise HTTPException(status_code=400, detail="User already exists")

    # 2️⃣ Crée contact Odoo
    odoo_contact_id = odoo.create_contact(profile.name, profile.email)
    if not odoo_contact_id:
        print("Erreur Odoo: contact non créé")

    # 3️⃣ Retourne statut
    return {"status": "ok", "odoo_contact_id": odoo_contact_id}

# ==================================================
# ODOO PROFLIE SAVE
# ==================================================
@router.post("/profile/save")
def save_profile(profile: UserProfile):
    # 1️⃣ Update ton DB SaaS ici
    contact_id = 1  # Récupère depuis DB le contact Odoo correspondant
    update_fields = {"name": profile.name, "email": profile.email}
    odoo.update_contact(contact_id, update_fields)
    return {"status": "ok"}

# ==================================================
# ODOO USER PORTFOLIO ANALYZE CRM
# ==================================================
@router.post("/portfolio/analyse/crm")
def portfolio_analyse(analysis: PortfolioAnalysis):
    # 1️⃣ Analyse portfeuille dans ton DB SaaS
    print("Analyse :", analysis.ai_advice)

    # 2️⃣ Si premium, créer opportunité CRM
    if analysis.premium:
        contact_id = 1  # récupère contact Odoo
        opportunity_title = "Portefeuille Premium à analyser"
        expected_revenue = analysis.total_value
        odoo.create_opportunity(contact_id, opportunity_title, expected_revenue)

    return {"status": "ok", "advice": analysis.ai_advice}


