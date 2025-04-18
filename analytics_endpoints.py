from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from supabase import Client

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Models for response data
class StudentAnalytics(BaseModel):
    id: str
    name: str
    org_id: str
    email: str
    language: str
    overall_mark: float
    average_mark: float
    recent_test_mark: float
    fluency_mark: float
    vocab_mark: float
    sentence_mastery: float
    pronunciation: float

class AnalyticsSummary(BaseModel):
    avg_overall: float
    avg_fluency: float
    avg_vocab: float
    avg_sentence_mastery: float
    avg_pronunciation: float
    weekly_improvement: float

class LanguageDetail(BaseModel):
    language_name: str
    total_students: int
    active_students: int
    tests_conducted: int
    pass_rate: int

@router.get("/students")
async def get_students_analytics(
    org_id: str = Query(..., description="Organization ID"),
    language: str = Query(..., description="Language filter")
):
    """
    Get analytics data for students in an organization filtered by language
    """
    try:
        # Get Supabase client from app state
        from main import supabase
        
        # Query students table with filters
        response = supabase.table("students") \
            .select("*") \
            .eq("org_id", org_id) \
            .eq("language", language) \
            .execute()
        
        if not response.data:
            return {"students": []}
        
        return {"students": response.data}
    except Exception as e:
        print(f"Error fetching student analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch student analytics")

@router.get("/summary")
async def get_analytics_summary(
    org_id: str = Query(..., description="Organization ID"),
    language: str = Query(..., description="Language filter")
):
    """
    Get summary analytics for a specific language in an organization
    """
    try:
        # Get Supabase client from app state
        from main import supabase
        
        # Query students table to calculate averages
        response = supabase.table("students") \
            .select("*") \
            .eq("org_id", org_id) \
            .eq("language", language) \
            .execute()
        
        if not response.data or len(response.data) == 0:
            # Return default values if no data
            return {
                "summary": {
                    "avg_overall": 0,
                    "avg_fluency": 0,
                    "avg_vocab": 0,
                    "avg_sentence_mastery": 0,
                    "avg_pronunciation": 0,
                    "weekly_improvement": 0
                }
            }
        
        # Calculate averages
        students = response.data
        avg_overall = sum(s.get("overall_mark", 0) for s in students) / len(students)
        avg_fluency = sum(s.get("fluency_mark", 0) for s in students) / len(students)
        avg_vocab = sum(s.get("vocab_mark", 0) for s in students) / len(students)
        avg_sentence_mastery = sum(s.get("sentence_mastery", 0) for s in students) / len(students)
        avg_pronunciation = sum(s.get("pronunciation", 0) for s in students) / len(students)
        
        # For weekly improvement, we would need historical data
        # Using a placeholder value for now
        weekly_improvement = 1.2
        
        return {
            "summary": {
                "avg_overall": round(avg_overall, 1),
                "avg_fluency": round(avg_fluency, 1),
                "avg_vocab": round(avg_vocab, 1),
                "avg_sentence_mastery": round(avg_sentence_mastery, 1),
                "avg_pronunciation": round(avg_pronunciation, 1),
                "weekly_improvement": weekly_improvement
            }
        }
    except Exception as e:
        print(f"Error fetching analytics summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics summary")

@router.get("/language-detail")
async def get_language_detail(
    org_id: str = Query(..., description="Organization ID"),
    language: str = Query(..., description="Language name")
):
    """
    Get detailed statistics for a specific language in an organization
    """
    try:
        # Get Supabase client from app state
        from main import supabase
        
        # Count students for this language
        students_response = supabase.table("students") \
            .select("*", count="exact") \
            .eq("org_id", org_id) \
            .eq("language", language) \
            .execute()
        
        total_students = students_response.count if hasattr(students_response, 'count') else len(students_response.data)
        
        # For other metrics, we would need additional tables/data
        # Using placeholder values for now
        active_students = int(total_students * 0.85)  # Assuming 85% are active
        tests_conducted = total_students * 4 // 10  # Rough estimate
        
        # Calculate pass rate (students with overall_mark >= 70)
        passing_students = sum(1 for s in students_response.data if s.get("overall_mark", 0) >= 70)
        pass_rate = int((passing_students / total_students) * 100) if total_students > 0 else 0
        
        return {
            "language_name": language,
            "total_students": total_students,
            "active_students": active_students,
            "tests_conducted": tests_conducted,
            "pass_rate": pass_rate
        }
    except Exception as e:
        print(f"Error fetching language details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch language details")