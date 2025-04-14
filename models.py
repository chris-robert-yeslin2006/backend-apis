from pydantic import BaseModel
from typing import Optional

# -------- ORGANIZATION MODELS --------
class OrganizationBase(BaseModel):
    name: str
    head: str
    ambassador_name: str
    ambassador_contact: str
    contact: str

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationOut(OrganizationBase):
    id: str

# class OrganizationCreate(BaseModel):
#     name: str
#     head: str
#     ambassador_name: str
#     ambassador_contact: str
#     contact: str


# -------- ADMIN MODELS --------
class AdminBase(BaseModel):
    name: str
    contact: str
    role: str     # e.g., “Coordinator”, “Head Admin”, etc.
    language: str # e.g., Japanese, Mandarin, etc.

# For creation, accept org_name instead of org_id
class AdminCreate(AdminBase):
    org_name: str  # <-- used to fetch org_id in backend

class AdminOut(AdminBase):
    id: str
    org_id: str
