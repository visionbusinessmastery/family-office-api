def calculate_yield(property):

    rent_estimated = property["surface"] * 10
    annual_rent = rent_estimated * 12

    return round((annual_rent / property["price"]) * 100, 2)
