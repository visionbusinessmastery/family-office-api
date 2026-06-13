import os


VISION_CONTACT = {
    "brand": "Vision Business Mastery",
    "title": "Contact et reseau",
    "description": "Retrouve Vision Business Mastery sur les principaux canaux officiels.",
    "email": os.getenv("VISION_CONTACT_EMAIL", "visionbusinessmastery@gmail.com"),
    "website": os.getenv(
        "VISION_CONTACT_WEBSITE",
        "https://vision-business-mastery.odoo.com/",
    ),
    "networks": [
        {
            "key": "email",
            "label": "Email",
            "url": "mailto:visionbusinessmastery@gmail.com",
            "display": "visionbusinessmastery@gmail.com",
            "icon": "mail",
        },
        {
            "key": "website",
            "label": "Site web",
            "url": "https://vision-business-mastery.odoo.com/",
            "display": "vision-business-mastery.odoo.com",
            "icon": "web",
        },
        {
            "key": "facebook",
            "label": "Facebook",
            "url": "https://www.facebook.com/visionbusinessmastery?locale=fr_FR",
            "display": "visionbusinessmastery",
            "icon": "facebook",
        },
        {
            "key": "linkedin",
            "label": "LinkedIn",
            "url": "https://www.linkedin.com/company/109513925/",
            "display": "Vision Business Mastery",
            "icon": "linkedin",
        },
        {
            "key": "youtube",
            "label": "YouTube",
            "url": "https://www.youtube.com/@VisionMasteryBusiness",
            "display": "@VisionMasteryBusiness",
            "icon": "youtube",
        },
        {
            "key": "instagram",
            "label": "Instagram",
            "url": "https://www.instagram.com/vision.business.97/",
            "display": "@vision.business.97",
            "icon": "instagram",
        },
        {
            "key": "tiktok",
            "label": "TikTok",
            "url": "https://www.tiktok.com/@vision.business.97",
            "display": "@vision.business.97",
            "icon": "tiktok",
        },
    ],
}


def get_contact_config():
    config = dict(VISION_CONTACT)
    config["networks"] = [dict(item) for item in VISION_CONTACT["networks"]]
    return config
