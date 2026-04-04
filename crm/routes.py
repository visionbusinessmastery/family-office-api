from fastapi import APIRouter
from crm.odoo import OdooClient

# ==================================================
# CONFIG ODOO
# ==================================================

router = APIRouter()
odoo = OdooClient()

# ==================================================
# CREATE LEAD ODOO
# ==================================================
@router.post("/lead")
def create_lead(name: str, email: str):
    contact_id = odoo.create_contact(name, email)
    return {"contact_id": contact_id}

    except Exception as e:
            print(f"Erreur création contact Odoo: {e}")
            return None

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
            
# ==================================================
# ODOO REGSITER
# ==================================================
@app.post("/odoo/register")
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
@app.post("/profile/save")
def save_profile(profile: UserProfile):
    # 1️⃣ Update ton DB SaaS ici
    contact_id = 1  # Récupère depuis DB le contact Odoo correspondant
    update_fields = {"name": profile.name, "email": profile.email}
    odoo.update_contact(contact_id, update_fields)
    return {"status": "ok"}

# ==================================================
# ODOO USER PORTFOLIO ANALYZE CRM
# ==================================================
@app.post("/portfolio/analyse/crm")
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


