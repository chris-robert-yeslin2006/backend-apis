from fastapi import APIRouter, HTTPException, Request
from typing import List
from pydantic import BaseModel
from main import supabase

router = APIRouter(prefix="/student-tests", tags=["student-tests"])

# Response model
class StudentTest(BaseModel):
    id: str
    test_name: str
    test_time: str
    test_duration: int
    test_link: str
    language: str
    status: str

@router.get("/upcoming", response_model=List[StudentTest])
async def get_student_tests(request: Request):
    try:
        # Get data from cookies
        user_id = request.cookies.get("user_id")
        language = request.cookies.get("language")
        if not user_id or not language:
            raise HTTPException(status_code=401, detail="Missing authentication info")

        # Fetch auth entry to get the email
        auth_response = supabase.table("auth").select("*").eq("id", user_id).execute()
        if not auth_response.data:
            raise HTTPException(status_code=404, detail="User not found")

        email = auth_response.data[0]["email"]

        # Fetch student by email
        student_response = supabase.table("students").select("*").eq("email", email).execute()
        if not student_response.data:
            raise HTTPException(status_code=404, detail="Student not found")

        student = student_response.data[0]
        org_id = student["org_id"]

        # Get tests for the student's org and language
        tests_response = (
            supabase.table("tests")
            .select("*")
            .eq("org_id", org_id)
            .eq("language", language)
            .eq("status", "upcoming")
            .order("test_time", desc=False)
            .execute()
        )

        return tests_response.data

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
