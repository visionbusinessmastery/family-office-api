import requests

def search_imodom(city: str):

    return [{
        "title": f"Annonce Imodom {city}",
        "price": 150000,
        "surface": 65,
        "source": "imodom"
    }]
