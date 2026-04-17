import requests
import os

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USERNAME = os.getenv("ODOO_USERNAME")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")


class OdooClient:

    def __init__(self):
        self.url = f"{ODOO_URL}/jsonrpc"
        self.uid = None

    # =========================
    # LOGIN LAZY (IMPORTANT)
    # =========================
    def login(self):
        if self.uid:
            return self.uid

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

        try:
            res = requests.post(self.url, json=payload, timeout=10).json()
            self.uid = res.get("result")
            return self.uid
        except Exception:
            return None

    # =========================
    # CREATE CONTACT
    # =========================
    def create_contact(self, name, email):

        uid = self.login()

        if not uid:
            return {"error": "Odoo unavailable"}

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB,
                    uid,
                    ODOO_PASSWORD,
                    "res.partner",
                    "create",
                    [{"name": name, "email": email}]
                ]
            },
            "id": 2
        }

        try:
            res = requests.post(self.url, json=payload, timeout=10).json()
            return res.get("result")
        except Exception as e:
            return {"error": str(e)}
