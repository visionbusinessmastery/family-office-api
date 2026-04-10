def calculate_yield(prop):

    rent_estimated = prop["surface"] * 10
    annual_rent = rent_estimated * 12

    return round((annual_rent / prop["price"]) * 100, 2)
