import requests
import os

def search_seloger(city: str):

    url = f"https://www.seloger.com/list.htm?ci=75056&cp={city}"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)

        # ⚠️ MVP : pas de parsing réel (HTML compliqué)
        return [{
            "title": f"Annonce SeLoger {city}",
            "price": 180000,
            "surface": 70,
            "source": "seloger"
        }]

    except:
        return []
