import os
from resend import Resend

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

if not RESEND_API_KEY:
    raise Exception("RESEND_API_KEY manquante")

resend = Resend(RESEND_API_KEY)

FRONT_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# =========================
# SEND EMAIL VERIFICATION
# =========================
def send_verification_email(to_email: str, token: str):

    verify_link = f"{FRONT_URL}/verify-email?token={token}"

    print("🔗 VERIFY LINK:", verify_link)

    try:
        response = resend.emails.send({
            "from": "Vision Business Mastery <onboarding@resend.dev>",
            "to": to_email,
            "subject": "Active ton compte Vision Business Mastery",
            "html": f"""
                <html>
                    <body style="font-family:Arial;">
                        <h2>Bienvenue 👋</h2>

                        <p>Pour activer ton compte :</p>

                        <a href="{verify_link}" style="
                            display:inline-block;
                            padding:12px 20px;
                            background:#1DA2CF;
                            color:white;
                            text-decoration:none;
                            border-radius:8px;
                        ">
                            Activer mon compte
                        </a>

                        <p style="margin-top:20px;font-size:12px;">
                            Si le bouton ne fonctionne pas :
                            <br/>
                            {verify_link}
                        </p>
                    </body>
                </html>
            """
        })

        print("✅ EMAIL SENT:", response)

    except Exception as e:
        print("❌ EMAIL ERROR:", str(e))
        raise
