from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from main import supabase

router = APIRouter(prefix="/student", tags=["students"])

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

@router.post("/add")
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
        print(f"adding Student data: {student_data}")
        
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


@router.get("/list")
async def list_students(org_id: str = None, language: str = None):
    try:
        print(f"Received request for students with org_id: {org_id} and language: {language}")
        
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
        
        if language:
            query = query.eq("language", language)
            
        response = query.execute()
        print(f"Students response: {response.data}")
        
        return {
            "students": response.data or [],
            "org_name": org_name
        }
    except Exception as e:
        print(f"Error fetching students: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch students")
    # try:
    #     print(f"Received request for students with org_id: {org_id}")
        
    #     # Get organization name separately
    #     org_name = None
    #     if org_id:
    #         org_response = supabase.table("organizations").select("name").eq("id", org_id).execute()
    #         print(f"Organization response: {org_response.data}")
            
    #         if org_response.data and len(org_response.data) > 0:
    #             org_name = org_response.data[0].get("name")
        
    #     # Get students with organization relationship
    #     query = supabase.table("students").select("*, organizations(name)")
        
    #     if org_id:
    #         query = query.eq("org_id", org_id)
            
    #     response = query.execute()
    #     print(f"Students response: {response.data}")
        
    #     return {
    #         "students": response.data or [],
    #         "org_name": org_name
    #     }
    # except Exception as e:
    #     print(f"Error fetching students: {str(e)}")
    #     raise HTTPException(status_code=500, detail="Failed to fetch students")

@router.get("/{student_id}")
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

@router.put("/{student_id}")
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

@router.delete("/{student_id}")
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