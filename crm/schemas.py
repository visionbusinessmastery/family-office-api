from pydantic import BaseModel, EmailStr

# =========================
# LEAD
# =========================
class LeadRequest(BaseModel):
    name: str
    email: EmailStr


# =========================
# CRM PROFILE
# =========================
class CRMProfile(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
