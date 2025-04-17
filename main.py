from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,EmailStr
from sqlalchemy.orm import Session
from supabase import create_client, Client
import bcrypt
import jwt
import os
from datetime import datetime, timedelta
import uuid
from typing import Optional

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zabdbbemkenayxfmevhj.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InphYmRiYmVta2VuYXl4Zm1ldmhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQwNTExMTIsImV4cCI6MjA1OTYyNzExMn0.yaXLtBRuGbIzRsyDLgoED5xXIfRK657uZ86D7al1sYw")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")  # Change in production

# Init Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# FastAPI app
app = FastAPI()

# CORS Middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/organization/list")
def list_organizations():
    response = supabase.table("organizations").select("*").execute()
    return {"organizations": response.data}
# Request model
class LoginRequest(BaseModel):
    email: str
    password: str
    org_id: str = None  # Make it optional

# Login route with debugging
@app.post("/auth/login")
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
        
        # Get organization ID for admin or student roles
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

class AdminCreate(BaseModel):
    name: str
    org_id: uuid.UUID
    role: str
    contact: str
    language: str
    email: EmailStr
    password: str

@app.post("admin/add")
async def add_admin(admin: AdminCreate):
    # Check if email already exists in auth table
    auth_check = supabase.table("auth").select("*").eq("email", admin.email).execute()
    if auth_check.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Add to admins table
    admin_response = supabase.table("admins").insert({
        "name": admin.name,
        "org_id": str(admin.org_id),
        "role": admin.role,
        "contact": admin.contact,
        "language": admin.language,
        "email": admin.email
    }).execute()
    
    # Add to auth table
    auth_response = supabase.table("auth").insert({
        "username": admin.name,
        "email": admin.email,
        "password": admin.password,  # Not hashed for now
        "role": "admin"
    }).execute()
    
    return {"success": True, "admin_id": admin_response.data[0]["id"]}
    print(f"\nLogin attempt for username: {payload.username}")
    
    try:
        # Fetch user by username
        response = supabase.table("auth").select("*").eq("username", payload.username).execute()
        
        if not response.data:
            print("⚠️ No user found with this username.")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user = response.data[0]
        print(f"🔎 User found: {user['username']} (Role: {user['role']})")
        
        # Password check (plaintext comparison for debugging)
        if payload.password != user["password"]:
            print("❌ Password mismatch.")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        print("✅ Authentication successful")
        
        # Get organization ID based on role
        org_id = None
        if user["role"] in ["admin", "student"]:
            table = "admins" if user["role"] == "admin" else "students"
            org_res = supabase.table(table).select("org_id").eq("username", user["username"]).execute()
            if org_res.data:
                org_id = org_res.data[0].get("org_id")
                print(f"🏢 Organization ID: {org_id}")

        # Generate JWT token
        token_data = {
            "sub": user["username"],
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")
        
        # Determine redirect path
        redirect_map = {
            "admin": "/admin/dashboard",
            "student": "/student/dashboard",
            "org": "/organization/dashboard",
            "individual": "/individual/dashboard"
        }
        
        return {
            "access_token": token,
            "role": user["role"],
            "username": user["username"],
            "org_id": org_id,
            "redirect": redirect_map.get(user["role"], "/")
        }
        
    except Exception as e:
        print(f"🔥 Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")