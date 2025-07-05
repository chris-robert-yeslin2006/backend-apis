from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zabdbbemkenayxfmevhj.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InphYmRiYmVta2VuYXl4Zm1ldmhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQwNTExMTIsImV4cCI6MjA1OTYyNzExMn0.yaXLtBRuGbIzRsyDLgoED5xXIfRK657uZ86D7al1sYw")
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")  # Change in production

# Print configurations
print(f"Supabase URL: {SUPABASE_URL}")
print(f"Supabase KEY: {SUPABASE_KEY}")

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

# Import routers
from routers.auth import router as auth_router
from routers.organizations import router as organizations_router
from routers.admins import router as admins_router
from routers.students import router as students_router
from analytics_endpoints import router as analytics_router

# Include routers
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(admins_router)
app.include_router(students_router)
app.include_router(analytics_router)

@app.get("/")
async def root():
    return {"message": "Language Learning API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)