from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from main import supabase

router = APIRouter(prefix="/admin", tags=["admins"])

class AdminCreate(BaseModel):
    name: str
    org_id: str  # Changed from uuid.UUID to str for flexibility
    role: str
    contact: str
    language: str
    email: EmailStr
    password: str

@router.post("/add")
async def add_admin(admin: AdminCreate):
    try:
        print(f"Attempting to add admin: {admin.email}")
        
        # Check if email already exists in auth table
        auth_check = supabase.table("auth").select("*").eq("email", admin.email).execute()
        if auth_check.data and len(auth_check.data) > 0:
            print(f"Email {admin.email} already exists")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Add to admins table
        admin_response = supabase.table("admins").insert({
            "name": admin.name,
            "org_id": admin.org_id,
            "role": admin.role,
            "contact": admin.contact,
            "language": admin.language,
            "email": admin.email
        }).execute()
        
        if not admin_response.data:
            print("Failed to insert into admins table")
            raise HTTPException(status_code=500, detail="Failed to create admin record")
        
        # Add to auth table
        auth_response = supabase.table("auth").insert({
            "username": admin.name,
            "email": admin.email,
            "password": admin.password,  # Not hashed for now
            "role": "admin"
        }).execute()
        
        if not auth_response.data:
            print("Failed to insert into auth table")
            # Rollback admins insert if possible
            raise HTTPException(status_code=500, detail="Failed to create auth record")
        
        print(f"Admin successfully added: {admin.email}")
        return {"success": True, "admin_id": admin_response.data[0]["id"]}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding admin: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/list")
async def list_admins(org_id: str = None):
    try:
        print(f"Received request for admins with org_id: {org_id}")
        
        # Get organization name separately
        org_name = None
        if org_id:
            org_response = supabase.table("organizations").select("name").eq("id", org_id).execute()
            print(f"Organization response: {org_response.data}")
            
            if org_response.data and len(org_response.data) > 0:
                org_name = org_response.data[0].get("name")
        
        # Get admins with organization relationship
        query = supabase.table("admins").select("*, organizations(name)")
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        print(f"Admins response: {response.data}")
        
        return {
            "admins": response.data or [],
            "org_name": org_name
        }
    except Exception as e:
        print(f"Error fetching admins: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch admins")

@router.get("/{admin_id}")
async def get_admin(admin_id: str):
    try:
        response = supabase.table("admins").select("*").eq("id", admin_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Admin not found")
            
        return {"admin": response.data[0]}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error fetching admin: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch admin details")

@router.put("/{admin_id}")
async def update_admin(admin_id: str, admin_data: dict):
    try:
        # Validate that the admin exists
        check_response = supabase.table("admins").select("*").eq("id", admin_id).execute()
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Admin not found")
            
        # Create update data for admin table
        update_data = {
            "name": admin_data.get("name"),
            "role": admin_data.get("role"),
            "contact": admin_data.get("contact"),
            "language": admin_data.get("language")
        }
        
        # Add email to update if provided
        if admin_data.get("email"):
            update_data["email"] = admin_data.get("email")
            
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        # Update admin in admins table
        admin_response = supabase.table("admins").update(update_data).eq("id", admin_id).execute()
        
        # Update auth table if needed
        admin_email = check_response.data[0].get("email")
        auth_update = {}
        
        # If name changed, update username in auth table
        if "name" in update_data:
            auth_update["username"] = update_data["name"]
            
        # If email changed, update email in auth table
        if "email" in update_data:
            new_email = update_data["email"]
            auth_update["email"] = new_email
            # Update admin_email for password update if needed
            admin_email = new_email
            
        # If password provided, update password in auth table
        if admin_data.get("password") and admin_data.get("password").strip():
            auth_update["password"] = admin_data.get("password")
            
        # Perform update if there are changes to auth table
        if auth_update and admin_email:
            auth_response = supabase.table("auth").update(auth_update).eq("email", admin_email).execute()
        
        return {"success": True, "admin": admin_response.data[0]}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error updating admin: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update admin")

@router.delete("/{admin_id}")
async def delete_admin(admin_id: str):
    try:
        # Get admin details including email
        admin_response = supabase.table("admins").select("email").eq("id", admin_id).execute()
        
        if not admin_response.data:
            raise HTTPException(status_code=404, detail="Admin not found")
            
        admin_email = admin_response.data[0].get("email")
        
        # Delete admin from admins table
        admin_delete = supabase.table("admins").delete().eq("id", admin_id).execute()
        
        # Delete admin from auth table if email is available
        if admin_email:
            auth_delete = supabase.table("auth").delete().eq("email", admin_email).execute()
        
        return {"success": True, "message": "Admin deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error deleting admin: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete admin")