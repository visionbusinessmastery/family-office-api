from fastapi import APIRouter

from company.contact_config import get_contact_config


router = APIRouter()


@router.get("/contact")
def get_company_contact():
    return get_contact_config()
