def calculate_yield(prop: dict):

    rent_estimated = prop["surface"] * 10
    annual_rent = rent_estimated * 12

    return round((annual_rent / prop["price"]) * 100, 2)
