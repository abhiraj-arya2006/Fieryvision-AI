from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import engine, Base
from app.api.router import router as api_router

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FieryVision AI Backend",
    description="Global industrial fire risk detection and satellite intelligence backend powered by NASA VIIRS & ML anomaly scoring.",
    version="1.0.0"
)

# Configure CORS for frontend access
allowed_origins = [
    settings.FRONTEND_URL,
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include main API router under /api
app.include_router(api_router, prefix="/api")

# Mount static frontend files under /app
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
frontend_path = frontend_dist if os.path.exists(frontend_dist) else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

@app.get("/")
def root():
    return {
        "service": "FieryVision AI Backend API",
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
        "frontend": "/app/"
    }

if __name__ == "__main__":
    import uvicorn
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(backend_dir)
    app_dir = os.path.join(backend_dir, "app")
    ml_dir = os.path.join(root_dir, "ml")
    
    watch_dirs = [app_dir]
    if os.path.exists(ml_dir):
        watch_dirs.append(ml_dir)
        
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=watch_dirs,
        reload_excludes=[
            "venv",
            ".venv",
            "*/venv/*",
            "*site-packages*",
            "node_modules",
            "*/node_modules/*",
            "data/cache",
            "*/data/cache/*",
            "*.pyc",
            "__pycache__",
            "*.db"
        ]
    )
