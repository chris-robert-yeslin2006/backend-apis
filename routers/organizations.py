from fastapi import APIRouter
from supabase_client import supabase

router = APIRouter()

@router.post("/add")
def add_organization(data: dict):
    name = data.get("name")
    if not name:
        return {"error": "Organization name required"}
    res = supabase.table("organizations").insert({"name": name}).execute()
    return res.data

@router.get("/all")
def get_all_organizations():
    res = supabase.table("organizations").select("*").execute()
    return res.data