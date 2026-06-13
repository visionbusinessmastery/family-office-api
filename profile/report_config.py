import os


VISION_BUSINESS_REPORT_CONFIG = {
    "brand": "WHITE ROCK",
    "company_name": "Vision Business",
    "subtitle": "Wealth Operating System",
    "logo_url": "/logo.png",
    "website": os.getenv("VISION_BUSINESS_WEBSITE", "https://vision-business.com"),
    "contact_email": os.getenv("VISION_BUSINESS_CONTACT_EMAIL", "contact@vision-business.com"),
    "footer_note": (
        "Synthese generee automatiquement a partir des donnees disponibles dans "
        "White Rock."
    ),
    "disclaimer": (
        "document informatif, non contractuel, ne constitue pas un conseil "
        "financier ou bancaire"
    ),
    "data_notice": (
        "Les donnees presentees sont declaratives et dependent des informations "
        "renseignees ou synchronisees dans le dashboard."
    ),
}


def get_report_config():
    return dict(VISION_BUSINESS_REPORT_CONFIG)
