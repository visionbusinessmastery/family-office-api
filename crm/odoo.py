import requests
import os

# ==================================================
# CONFIG ODOO
# ==================================================

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

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
