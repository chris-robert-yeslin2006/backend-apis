from fastapi import APIRouter
from supabase_client import supabase

router = APIRouter()

VALID_LANGUAGES = ['Japanese', 'Mandarin', 'German', 'Spanish', 'French', 'English']

@router.post("/add")
def add_admin(data: dict):
    email = data.get("email")
    org_id = data.get("org_id")
    language = data.get("language")

    if not email or not org_id or not language:
        return {"error": "Missing fields"}

    if language not in VALID_LANGUAGES:
        return {"error": "Invalid language"}

    res = supabase.table("admins").insert({
        "email": email,
        "org_id": org_id,
        "language": language
    }).execute()
    return res.data

@router.get("/all")
def get_all_admins():
    res = supabase.table("admins").select("*, organizations(name)").execute()
    return res.data