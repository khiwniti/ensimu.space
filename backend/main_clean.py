"""
Clean, minimal FastAPI server for EnsumuSpace.
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    print("🚀 EnsumuSpace API starting up...")
    yield
    print("🛑 EnsumuSpace API shutting down...")


# Create the FastAPI app
app = FastAPI(
    title="EnsumuSpace API",
    description="AI-powered Computer-Aided Engineering platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to EnsumuSpace API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ensumu-space-api"
    }


# API Routes
@app.get("/api/projects")
async def get_projects():
    """Get all projects."""
    return {
        "projects": [],
        "total": 0
    }


@app.post("/api/projects")
async def create_project():
    """Create a new project."""
    return {
        "id": "proj_1",
        "name": "New Project",
        "status": "created"
    }


@app.get("/api/simulations")
async def get_simulations():
    """Get all simulations."""
    return {
        "simulations": [],
        "total": 0
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_clean:app",
        host="0.0.0.0", 
        port=8001,
        reload=True
    )