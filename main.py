from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import bcrypt
import jwt
import os
from datetime import datetime, timedelta

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

@app.get("/auth/organizations")
def get_organizations():
    # Fetch organization names from the organizations table
    org_resp = supabase.table("organizations").select("id", "name").execute()
    if not org_resp.data:
        raise HTTPException(status_code=404, detail="No organizations found")
    return org_resp.data