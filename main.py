from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from supabase import create_client, Client
import jwt
import os
from datetime import datetime, timedelta
import uuid
from typing import Optional

# Import the analytics router
from analytics_endpoints import router as analytics_router

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

# Include the analytics router
app.include_router(analytics_router)

@app.get("/organization/list")
def list_organizations():
    response = supabase.table("organizations").select("*").execute()
    return {"organizations": response.data}

# Request model
class LoginRequest(BaseModel):
    email: str
    password: str
    org_id: Optional[str] = None

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

class AdminCreate(BaseModel):
    name: str
    org_id: str  # Changed from uuid.UUID to str for flexibility
    role: str
    contact: str
    language: str
    email: EmailStr
    password: str

@app.post("/admin/add")  # Fixed: Added the leading slash
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

@app.get("/admin/list")
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

@app.get("/admin/{admin_id}")
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

@app.put("/admin/{admin_id}")
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

@app.delete("/admin/{admin_id}")
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

    # Add these routes to your main.py file

class StudentCreate(BaseModel):
    name: str
    org_id: str
    language: str
    email: EmailStr
    password: str
    overall_mark: Optional[float] = None
    average_mark: Optional[float] = None
    recent_test_mark: Optional[float] = None
    fluency_mark: Optional[float] = None
    vocab_mark: Optional[float] = None
    sentence_mastery: Optional[float] = None
    pronunciation: Optional[float] = None

@app.post("/student/add")
async def add_student(student: StudentCreate):
    try:
        print(f"Attempting to add student: {student.email}")
        
        # Check if email already exists in auth table
        auth_check = supabase.table("auth").select("*").eq("email", student.email).execute()
        if auth_check.data and len(auth_check.data) > 0:
            print(f"Email {student.email} already exists")
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create student marks data dictionary
        student_data = {
            "name": student.name,
            "org_id": student.org_id,
            "email": student.email,
            "language": student.language
        }
        
        # Add optional mark fields if provided
        if student.overall_mark is not None:
            student_data["overall_mark"] = student.overall_mark
        if student.average_mark is not None:
            student_data["average_mark"] = student.average_mark
        if student.recent_test_mark is not None:
            student_data["recent_test_mark"] = student.recent_test_mark
        if student.fluency_mark is not None:
            student_data["fluency_mark"] = student.fluency_mark
        if student.vocab_mark is not None:
            student_data["vocab_mark"] = student.vocab_mark
        if student.sentence_mastery is not None:
            student_data["sentence_mastery"] = student.sentence_mastery
        if student.pronunciation is not None:
            student_data["pronunciation"] = student.pronunciation
        
        # Add to students table
        student_response = supabase.table("students").insert(student_data).execute()
        
        if not student_response.data:
            print("Failed to insert into students table")
            raise HTTPException(status_code=500, detail="Failed to create student record")
        
        # Add to auth table
        auth_response = supabase.table("auth").insert({
            "username": student.name,
            "email": student.email,
            "password": student.password,
            "role": "student"
        }).execute()
        
        if not auth_response.data:
            print("Failed to insert into auth table")
            # Rollback students insert if possible
            raise HTTPException(status_code=500, detail="Failed to create auth record")
        
        print(f"Student successfully added: {student.email}")
        return {"success": True, "student_id": student_response.data[0]["id"]}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error adding student: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/student/list")
async def list_students(org_id: str = None):
    try:
        print(f"Received request for students with org_id: {org_id}")
        
        # Get organization name separately
        org_name = None
        if org_id:
            org_response = supabase.table("organizations").select("name").eq("id", org_id).execute()
            print(f"Organization response: {org_response.data}")
            
            if org_response.data and len(org_response.data) > 0:
                org_name = org_response.data[0].get("name")
        
        # Get students with organization relationship
        query = supabase.table("students").select("*, organizations(name)")
        
        if org_id:
            query = query.eq("org_id", org_id)
            
        response = query.execute()
        print(f"Students response: {response.data}")
        
        return {
            "students": response.data or [],
            "org_name": org_name
        }
    except Exception as e:
        print(f"Error fetching students: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch students")

@app.get("/student/{student_id}")
async def get_student(student_id: str):
    try:
        response = supabase.table("students").select("*").eq("id", student_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Student not found")
            
        return {"student": response.data[0]}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error fetching student: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch student details")

@app.put("/student/{student_id}")
async def update_student(student_id: str, student_data: dict):
    try:
        # Validate that the student exists
        check_response = supabase.table("students").select("*").eq("id", student_id).execute()
        if not check_response.data:
            raise HTTPException(status_code=404, detail="Student not found")
            
        # Create update data for student table
        update_data = {
            "name": student_data.get("name"),
            "language": student_data.get("language"),
            "overall_mark": student_data.get("overall_mark"),
            "average_mark": student_data.get("average_mark"),
            "recent_test_mark": student_data.get("recent_test_mark"),
            "fluency_mark": student_data.get("fluency_mark"),
            "vocab_mark": student_data.get("vocab_mark"),
            "sentence_mastery": student_data.get("sentence_mastery"),
            "pronunciation": student_data.get("pronunciation")
        }
        
        # Add email to update if provided
        if student_data.get("email"):
            update_data["email"] = student_data.get("email")
            
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        # Update student in students table
        student_response = supabase.table("students").update(update_data).eq("id", student_id).execute()
        
        # Update auth table if needed
        student_email = check_response.data[0].get("email")
        auth_update = {}
        
        # If name changed, update username in auth table
        if "name" in update_data:
            auth_update["username"] = update_data["name"]
            
        # If email changed, update email in auth table
        if "email" in update_data:
            new_email = update_data["email"]
            auth_update["email"] = new_email
            # Update student_email for password update if needed
            student_email = new_email
            
        # If password provided, update password in auth table
        if student_data.get("password") and student_data.get("password").strip():
            auth_update["password"] = student_data.get("password")
            
        # Perform update if there are changes to auth table
        if auth_update and student_email:
            auth_response = supabase.table("auth").update(auth_update).eq("email", student_email).execute()
        
        return {"success": True, "student": student_response.data[0]}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error updating student: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update student")

@app.delete("/student/{student_id}")
async def delete_student(student_id: str):
    try:
        # Get student details including email
        student_response = supabase.table("students").select("email").eq("id", student_id).execute()
        
        if not student_response.data:
            raise HTTPException(status_code=404, detail="Student not found")
            
        student_email = student_response.data[0].get("email")
        
        # Delete student from students table
        student_delete = supabase.table("students").delete().eq("id", student_id).execute()
        
        # Delete student from auth table if email is available
        if student_email:
            auth_delete = supabase.table("auth").delete().eq("email", student_email).execute()
        
        return {"success": True, "message": "Student deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error deleting student: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete student")
