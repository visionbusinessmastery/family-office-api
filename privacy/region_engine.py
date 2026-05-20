EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
    "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
    "RO", "SK", "SI", "ES", "SE",
}


def detect_privacy_region(country: str | None = None, province: str | None = None):
    country_code = str(country or "").upper()
    province_code = str(province or "").upper()

    if country_code in EU_COUNTRIES:
        return {
            "region": "EU",
            "frameworks": ["RGPD"],
            "requires_cookie_opt_in": True,
            "requires_explicit_ai_consent": True,
        }

    if country_code == "CA" and province_code in ["QC", "QUEBEC", "QUÉBEC"]:
        return {
            "region": "QUEBEC",
            "frameworks": ["Loi 25", "PIPEDA"],
            "requires_cookie_opt_in": True,
            "requires_explicit_ai_consent": True,
        }

    if country_code == "CA":
        return {
            "region": "CANADA",
            "frameworks": ["PIPEDA"],
            "requires_cookie_opt_in": True,
            "requires_explicit_ai_consent": True,
        }

    return {
        "region": "INTERNATIONAL",
        "frameworks": ["Privacy by Design"],
        "requires_cookie_opt_in": False,
        "requires_explicit_ai_consent": True,
    }
