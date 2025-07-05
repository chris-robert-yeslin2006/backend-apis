from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt

# JWT Secret import
from main import JWT_SECRET, supabase

router = APIRouter(prefix="/auth", tags=["authentication"])

# Request model
class LoginRequest(BaseModel):
    email: str
    password: str
    org_id: Optional[str] = None

# Login route with debugging
@router.post("/login")
async def login_user(payload: LoginRequest, request: Request):
    print(f"\nLogin attempt from IP: {request.client.host}")
    print(f"Email received: {payload.email}")
    print(f"Password received: {payload.password}")
    
    try:
        # Fetch user from Supabase auth table
        response = supabase.table("auth").select("*").eq("email", payload.email).execute()
        
        if response.data is None or len(response.data) == 0:
            print("⚠️ No user found with this email.")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = response.data[0]
        
        print(f"🔎 User found in DB: {user}")
        print(f"🔐 Password in DB: {user['password']}")
        
        # Direct password comparison (plain text)
        if payload.password != user["password"]:
            print("❌ Password mismatch.")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        print("✅ Password matched.")
        
        # Get organization ID based on user role
        org_id = None
        if user["role"] == "admin":
            # Get admin's organization ID
            admin_resp = supabase.table("admins").select("org_id").eq("email", user["email"]).execute()
            if admin_resp.data and len(admin_resp.data) > 0:
                org_id = admin_resp.data[0].get("org_id")
        elif user["role"] == "student":
            # Get student's organization ID
            student_resp = supabase.table("students").select("org_id").eq("email", user["email"]).execute()
            if student_resp.data and len(student_resp.data) > 0:
                org_id = student_resp.data[0].get("org_id")
        elif user["role"] == "org":
            # Get organization's ID directly from organizations table
            org_resp = supabase.table("organizations").select("id").eq("email", user["email"]).execute()
            if org_resp.data and len(org_resp.data) > 0:
                org_id = org_resp.data[0].get("id")
                print(f"Found org_id for organization: {org_id}")
            else:
                print("⚠️ Could not find organization ID for this org user")
        
        # Generate JWT
        token_data = {
            "user_id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
        
        # Determine redirect based on role
        redirect_path = "/individual" if user["role"] == "individual" else "/organization"
        
        print("🎟️ JWT Token generated.")
        return {
            "access_token": token,
            "role": user["role"],
            "username": user["username"],
            "org_id": org_id,
            "redirect": redirect_path
        }
    
    except Exception as e:
        print("🔥 Exception during login:", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")