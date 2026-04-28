import os
import requests

# =========================
# CONFIG
# =========================
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

ENV = os.getenv("ENV", "dev")

FRONTEND_URL = (
    os.getenv("FRONTEND_URL_PROD")
    if ENV == "prod"
    else os.getenv("FRONTEND_URL_DEV", "http://localhost:3000")
)

if not RESEND_API_KEY:
    raise Exception("Missing RESEND_API_KEY")


# =========================
# SEND VERIFICATION EMAIL
# =========================
def send_verification_email(to_email: str, token: str):

    url = "https://api.resend.com/emails"

    verification_link = f"{FRONTEND_URL}/verify-email?token={token}"

    payload = {
        "from": "Vision Business Mastery <onboarding@vision-business.com>",
        "to": [to_email],
        "subject": "🚀 Vérifie ton email - Vision Business Mastery",
        "html": f"""
        <div style="font-family: Arial; text-align: center; padding: 20px;">
            
            <h2 style="color:#1DA2CF;">Bienvenue 🚀</h2>

            <p>
                Clique sur le bouton ci-dessous pour activer ton compte
            </p>

            <a href="{verification_link}" 
               style="
                    display:inline-block;
                    padding:12px 24px;
                    margin-top:20px;
                    background:#1DA2CF;
                    color:white;
                    text-decoration:none;
                    border-radius:8px;
               ">
                Vérifier mon compte
            </a>

            <p style="margin-top:20px; font-size:12px; color:gray;">
                Si le bouton ne fonctionne pas, copie ce lien :
            </p>

            <p style="font-size:12px;">
                {verification_link}
            </p>

        </div>
        """,
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    # =========================
    # SAFE CALL (NE CASSE PLUS REGISTER)
    # =========================
    try:
        response = requests.post(url, json=payload, headers=headers)

        print("📩 RESEND STATUS:", response.status_code)
        print("📩 RESEND BODY:", response.text)
        print("📨 SENDING EMAIL TO:", to_email)

        # ⚠️ IMPORTANT : on ne bloque PAS le register
        if response.status_code not in [200, 201]:
            print("⚠️ EMAIL FAILED BUT USER STILL CREATED")
            print("DETAIL:", response.text)

    except Exception as e:
        print("❌ EMAIL ERROR (NON BLOQUANT):", str(e))
        # ❗ on ne raise PLUS
        # sinon ton register crash

