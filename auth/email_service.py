import os
import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

def send_verification_email(to_email: str, token: str):
    url = "https://api.resend.com/emails"

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    verification_link = f"https://ton-frontend.com/verify-email?token={token}"

    payload = {
        "from": "Vision Business Mastery <onboarding@resend.dev>",
        "to": [to_email],
        "subject": "Vérifie ton email",
        "html": f"""
            <h2>Bienvenue 🚀</h2>
            <p>Confirme ton email ici :</p>
            <a href="{verification_link}">Vérifier mon compte</a>
        """,
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Erreur email: {response.text}")
