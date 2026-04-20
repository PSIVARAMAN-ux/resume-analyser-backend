from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import api_router
from core.database import engine
from models.base import Base

# Create Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume to Job AI API", version="1.0.0")

# Setup CORS to allow connections from local React frontend
origins = [
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:5173",
    "https://resume-analyser-frontend-wine.vercel.app/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include main router
app.include_router(api_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running"}
