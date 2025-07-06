# routers/tests.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime,timedelta
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler # type: ignore
from apscheduler.triggers.date import DateTrigger # type: ignore
from main import supabase

router = APIRouter(prefix="/tests", tags=["tests"])

class TestCreate(BaseModel):
    test_name: str
    auth_id: str  # ID from auth tablex
    org_id: str
    language: str
    test_duration: int
    test_time: datetime
    test_link: Optional[str] = None
    status: Optional[str] = "upcoming"

class TestResponse(BaseModel):
    id: str
    test_name: str
    org_id: str
    user_id: str
    language: str
    test_duration: int
    test_time: str
    test_link: Optional[str]
    status: str
    created_at: str

class TestUpdate(BaseModel):
    test_name: Optional[str] = None
    test_duration: Optional[int] = None
    test_time: Optional[datetime] = None
    test_link: Optional[str] = None
    status: Optional[str] = None

scheduler = AsyncIOScheduler()
async def update_test_status_to_completed(test_id: str):
    try:
        # Update the test status to completed
        response = supabase.table("tests").update({
            "status": "completed"
        }).eq("id", test_id).execute()
        
        print(f"Test {test_id} status updated to completed")
    except Exception as e:
        print(f"Error updating test status: {e}")

# Add this function to schedule status updates
async def schedule_test_completion(test_id: str, test_time: datetime, duration_minutes: int):
    # Calculate when the test should be completed
    completion_time = test_time + timedelta(minutes=duration_minutes)
    
    # Schedule the status update
    scheduler.add_job(
        update_test_status_to_completed,
        trigger=DateTrigger(run_date=completion_time),
        args=[test_id],
        id=f"complete_test_{test_id}",
        replace_existing=True
    )
    
    print(f"Scheduled test {test_id} to complete at {completion_time}")

@router.post("/add")
async def add_test(test: TestCreate):
    try:
        # Verify the auth user exists and is an admin
        auth_user = supabase.table("auth").select("*").eq("id", test.auth_id).execute()
        if not auth_user.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        auth_data = auth_user.data[0]
        if auth_data["role"] != "admin":
            raise HTTPException(status_code=403, detail="Only admins can create tests")

        # Get the admin details from admins table
        admin = supabase.table("admins").select("*").eq("email", auth_data["email"]).execute()
        if not admin.data:
            raise HTTPException(status_code=404, detail="Admin profile not found")

        admin_data = admin.data[0]

        # Prepare test data
        test_data = {
            "test_name": test.test_name,
            "org_id": test.org_id,
            "user_id": admin_data["id"],
            "language": test.language,
            "test_duration": test.test_duration,
            "test_time": test.test_time.isoformat(),
            "test_link": test.test_link,
            "status": test.status
        }

        # Insert into tests table
        response = supabase.table("tests").insert(test_data).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create test")

        return {
            "status": "success",
            "test": response.data[0],
            "admin": admin_data
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=List[TestResponse])
async def list_tests(
    auth_id: str,
    status: Optional[str] = None,
    language: Optional[str] = None
):
    try:
        # 1. Get admin info from auth_id
        auth_user = supabase.table("auth").select("*").eq("id", auth_id).execute()
        if not auth_user.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        auth_data = auth_user.data[0]
        
        # 2. Get admin details to find the admin's language if not specified
        admin = supabase.table("admins").select("*").eq("email", auth_data["email"]).execute()
        if not admin.data:
            raise HTTPException(status_code=404, detail="Admin profile not found")
        
        admin_data = admin.data[0]
        admin_language = language or admin_data["language"]
        admin_id = admin_data["id"]

        # 3. Build query
        query = supabase.table("tests").select("*").eq("user_id", admin_id)
        
        if status:
            query = query.eq("status", status)
        if admin_language:
            query = query.eq("language", admin_language)

        # 4. Execute query
        response = query.order("test_time", desc=True).execute()
        
        return response.data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# Add these classes at the top with your other models


@router.delete("/{test_id}")
async def delete_test(test_id: str, auth_id: str = None):
    try:
        # First, verify the test exists and belongs to the user
        test_response = supabase.table("tests").select("*").eq("id", test_id).execute()
        if not test_response.data:
            raise HTTPException(status_code=404, detail="Test not found")
        
        test_data = test_response.data[0]
        
        # Optional: Verify ownership if auth_id is provided
        if auth_id:
            auth_user = supabase.table("auth").select("*").eq("id", auth_id).execute()
            if not auth_user.data:
                raise HTTPException(status_code=404, detail="User not found")
            
            auth_data = auth_user.data[0]
            admin = supabase.table("admins").select("*").eq("email", auth_data["email"]).execute()
            if not admin.data:
                raise HTTPException(status_code=404, detail="Admin profile not found")
            
            admin_data = admin.data[0]
            if test_data["user_id"] != admin_data["id"]:
                raise HTTPException(status_code=403, detail="Not authorized to delete this test")
        
        # Delete the test
        delete_response = supabase.table("tests").delete().eq("id", test_id).execute()
        
        if not delete_response.data:
            raise HTTPException(status_code=500, detail="Failed to delete test")
        
        return {"status": "success", "message": "Test deleted successfully"}
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{test_id}")
async def update_test(test_id: str, test_update: TestUpdate):
    try:
        # First, verify the test exists
        test_response = supabase.table("tests").select("*").eq("id", test_id).execute()
        if not test_response.data:
            raise HTTPException(status_code=404, detail="Test not found")
        
        # Prepare update data (only include fields that are provided)
        update_data = {}
        if test_update.test_name is not None:
            update_data["test_name"] = test_update.test_name
        if test_update.test_duration is not None:
            update_data["test_duration"] = test_update.test_duration
        if test_update.test_time is not None:
            update_data["test_time"] = test_update.test_time.isoformat()
        if test_update.test_link is not None:
            update_data["test_link"] = test_update.test_link
        if test_update.status is not None:
            update_data["status"] = test_update.status
        
        # Update the test
        response = supabase.table("tests").update(update_data).eq("id", test_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update test")
        
        return {
            "status": "success", 
            "test": response.data[0],
            "message": "Test updated successfully"
        }
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    