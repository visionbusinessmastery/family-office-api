import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

FRONT_URL = os.getenv("FRONT_URL", "http://localhost:3000")


def send_verification_email(to_email: str, token: str):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        raise Exception("EMAIL_SENDER ou EMAIL_PASSWORD manquant")

    verify_link = f"{FRONT_URL}/verify-email?token={token}"

    print("🔗 VERIFY LINK:", verify_link)

    subject = "Active ton compte Vision Business Mastery"

    # 👉 VERSION HTML (mieux que texte brut)
    html_content = f"""
    <html>
        <body>
            <h2>Bienvenue 👋</h2>
            <p>Pour activer ton compte, clique ici :</p>
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

            <p style="margin-top:20px;">
                Ou copie ce lien :
                <br/>
                {verify_link}
            </p>
        </body>
    </html>
    """

    try:
        print("📡 Connexion SMTP...")

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()

        print("🔐 Login SMTP...")
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email

        msg.attach(MIMEText(html_content, "html"))

        print("📤 Envoi email à:", to_email)

        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        server.quit()

        print("✅ EMAIL SENT SUCCESS")

    except Exception as e:
        print("❌ EMAIL ERROR:", str(e))
        raise
