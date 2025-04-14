from fastapi import FastAPI, HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from models import OrganizationCreate, AdminCreate
import os
from fastapi.responses import JSONResponse
from fastapi import Path
from fastapi import Body
from fastapi import Form
from auth_utils import create_access_token, verify_password
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Supabase URL:", SUPABASE_URL)
print("Supabase KEY:", SUPABASE_KEY)

@app.post("/organization/add")
def add_organization(org: OrganizationCreate):
    existing = supabase.table("organizations").select("*").eq("name", org.name).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Organization already exists")

    response = supabase.table("organizations").insert({
        "name": org.name,
        "head": org.head,
        "ambassador_name": org.ambassador_name,
        "ambassador_contact": org.ambassador_contact,
        "contact": org.contact
    }).execute()

    return {"message": "Organization added", "data": response.data}

@app.get("/organization/list")
def list_organizations():
    response = supabase.table("organizations").select("*").execute()
    return {"organizations": response.data}

@app.post("/admin/add")
def add_admin(admin: AdminCreate):
    # Step 1: Lookup organization by name
    org_lookup = supabase.table("organizations").select("id").eq("name", admin.org_name).execute()

    if not org_lookup.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_id = org_lookup.data[0]['id']

    # Step 2: Insert admin using resolved org_id
    response = supabase.table("admins").insert({
        "name": admin.name,
        "org_id": org_id,
        "contact": admin.contact,
        "role": admin.role,
        "language": admin.language
    }).execute()

    return {"message": "Admin added", "data": response.data}

@app.get("/admin/list")
def list_admins(org_id: str = Query(default=None)):
    query = supabase.table("admins").select("id, name, contact, role, language, created_at, organizations(name)")

    if org_id:
        query = query.eq("org_id", org_id)
    
    response = query.execute()
    return {"admins": response.data}

@app.get("/analytics/students")
def get_students_for_analytics(org_id: str = Query(...), language: str = Query(...)):
    """
    Fetch students for a specific organization and language
    """
    response = supabase.table("students").select(
        "id, name, email, language, overall_mark, average_mark, recent_test_mark, "
        "fluency_mark, vocab_mark, sentence_mastery, pronunciation"
    ).eq("org_id", org_id).eq("language", language).execute()

    return {"students": response.data}

@app.get("/analytics/summary")
def get_summary_for_language(org_id: str = Query(...), language: str = Query(...)):
    """
    Provide summary statistics (like averages) for a given organization and language
    """
    response = supabase.table("students").select(
        "overall_mark, fluency_mark, vocab_mark, pronunciation"
    ).eq("org_id", org_id).eq("language", language).execute()

    data = response.data
    if not data:
        return {"summary": {}}

    # Compute averages
    total = len(data)
    summary = {
        "avg_overall": sum(s["overall_mark"] for s in data) / total,
        "avg_fluency": sum(s["fluency_mark"] for s in data) / total,
        "avg_vocab": sum(s["vocab_mark"] for s in data) / total,
        "avg_pronunciation": sum(s["pronunciation"] for s in data) / total,
    }

    return {"summary": summary}

@app.get("/analytics/language-detail")
def get_language_detail(org_id: str, language: str):
    students = supabase.table("students").select("*")\
        .eq("org_id", org_id).eq("language", language).execute().data

    if not students:
        return {"message": "No data", "total_students": 0}

    average = sum(s["overall_mark"] for s in students) / len(students)
    top_student = max(students, key=lambda s: s["overall_mark"])

    return {
        "language": language,
        "total_students": len(students),
        "average_mark": average,
        "top_student": {
            "name": top_student["name"],
            "overall_mark": top_student["overall_mark"]
        }
    }

@app.put("/organization/update/{org_id}")
def update_organization(org_id: str, updated_data: dict = Body(...)):
    existing = supabase.table("organizations").select("*").eq("id", org_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    response = supabase.table("organizations").update(updated_data).eq("id", org_id).execute()

    return {"message": "Organization updated", "data": response.data}

@app.delete("/organization/delete/{org_id}")
def delete_organization(org_id: str = Path(..., description="The ID of the organization to delete")):
    existing = supabase.table("organizations").select("*").eq("id", org_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    response = supabase.table("organizations").delete().eq("id", org_id).execute()
    return {"message": "Organization deleted", "data": response.data}

@app.post("/auth/login")
def login(email: str = Form(...), password: str = Form(...)):
    user_data = supabase.table("super_admins").select("*").eq("email", email).single().execute()

    if not user_data.data or not verify_password(password, user_data.data["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user_data.data["email"]})
    return {"access_token": token, "token_type": "bearer"}