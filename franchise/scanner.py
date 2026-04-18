def scan_franchise_opportunities(budget, risk, country, sector=None):

    database = [
        {
            "name": "Fitness Park",
            "entry_fee": 15000,
            "roi": 18,
            "risk": "medium",
            "sector": "fitness"
        },
        {
            "name": "Coffee Shop Local",
            "entry_fee": 8000,
            "roi": 12,
            "risk": "low",
            "sector": "food"
        },
        {
            "name": "Dark Kitchen",
            "entry_fee": 5000,
            "roi": 25,
            "risk": "high",
            "sector": "food"
        },
        {
            "name": "Cleaning Services Franchise",
            "entry_fee": 3000,
            "roi": 20,
            "risk": "low",
            "sector": "services"
        }
    ]

    results = []

    for f in database:

        if f["entry_fee"] <= budget:

            if sector and f["sector"] != sector:
                continue

            if risk == "low" and f["risk"] == "high":
                continue

            results.append(f)

    return sorted(results, key=lambda x: x["roi"], reverse=True)
