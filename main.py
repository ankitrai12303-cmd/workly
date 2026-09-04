import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.database import init_db, DB_PATH
from backend.seed_data import seed_database
from backend.api_routes import router as api_router

# Ensure DB initialized
if not DB_PATH.exists():
    print("Database not found. Initializing and seeding initial data...")
    seed_database()
else:
    init_db()

app = FastAPI(
    title="SkillBridge - Cooperative Gig Services Platform",
    description="A worker-centric digital marketplace connecting customers with verified cooperative service providers through fair matching, intelligent workforce planning, welfare support, and democratic cooperative governance.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "SkillBridge API is running. Access /docs for Swagger UI or place index.html in /static."}

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SkillBridge Cooperative Platform",
        "version": "1.0.0",
        "sih_problem_statement": "26089"
    }

if __name__ == "__main__":
    print("Starting SkillBridge platform on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
