import os
import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def send_verification_email(to_email: str, token: str):
    if not RESEND_API_KEY:
        raise Exception("RESEND_API_KEY manquante")

    url = "https://api.resend.com/emails"

    # =========================
    # LINK DYNAMIQUE (IMPORTANT)
    # =========================
    verification_link = f"{FRONTEND_URL}/verify-email?token={token}"

    # =========================
    # FROM EMAIL (IMPORTANT)
    # =========================
    # ⚠️ Tu pourras remplacer par ton domaine plus tard :
    # "Vision Business Mastery <onboarding@vision-business.com>"
    from_email = os.getenv(
        "EMAIL_FROM",
        "Vision Business Mastery <onboarding@resend.dev>"
    )

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": "🚀 Vérifie ton email - Vision Business Mastery",
        "html": f"""
        <div style="font-family:Arial;padding:20px;">
            <h2>Bienvenue 🚀</h2>

            <p>
                Clique sur le bouton ci-dessous pour activer ton compte :
            </p>

            <a href="{verification_link}" 
               style="
                 display:inline-block;
                 padding:12px 20px;
                 background:#1DA2CF;
                 color:white;
                 text-decoration:none;
                 border-radius:8px;
                 margin-top:10px;
               ">
               Vérifier mon compte
            </a>

            <p style="margin-top:20px;font-size:12px;color:#888;">
                Si tu n’as pas demandé cet email, ignore-le.
            </p>
        </div>
        """,
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        print("📧 RESEND STATUS:", response.status_code)
        print("📧 RESEND RESPONSE:", response.text)

        if response.status_code >= 300:
            raise Exception(f"Erreur email Resend: {response.text}")

    except Exception as e:
        print("❌ EMAIL ERROR:", str(e))
        raise Exception("Erreur envoi email")

