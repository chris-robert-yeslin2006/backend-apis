from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid

from main import supabase

router = APIRouter(prefix="/organization", tags=["organizations"])

@router.get("/list")
def list_organizations():
    response = supabase.table("organizations").select("*").execute()
    return {"organizations": response.data}

# Additional organization-related endpoints can be added here
