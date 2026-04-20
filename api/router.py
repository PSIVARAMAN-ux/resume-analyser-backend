from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.pdf_service import extract_text_from_pdf
from services.ai_service import ai_service
from core.database import get_db
from models.base import ApplicationHistory

api_router = APIRouter()

@api_router.get("/")
def read_root():
    return {"message": "Welcome to Resume-to-Job API"}

@api_router.post("/generate")
async def generate_application(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db)
):
    if not resume.filename.lower().endswith('.pdf') and resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    try:
        # Read file bytes directly from memory
        file_bytes = await resume.read()
        
        # 1. Parse PDF directly from bytes
        resume_text = extract_text_from_pdf(file_bytes)
        
        # 2. Call OpenAI Service via Groq
        result_json = await ai_service.generate_tailored_application(
            resume_text=resume_text,
            job_description=job_description
        )
        
        # 3. Save to database synchronously within scope
        db_record = ApplicationHistory(
            job_title=result_json.get("job_title", "Unknown Role"),
            match_score=result_json.get("match_score", 0),
            cover_letter=result_json.get("cover_letter", "")
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        return result_json
        
    except ValueError as ve:
        # Client errors (e.g., bad AI init, unreadable PDF)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Standard internal errors
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

class EnhanceRequest(BaseModel):
    draft_text: str

@api_router.post("/enhance-jd")
async def enhance_jd(req: EnhanceRequest):
    try:
        enhanced = await ai_service.enhance_job_description(req.draft_text)
        return {"enhanced_text": enhanced}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/history")
def fetch_history(db: Session = Depends(get_db)):
    # Retrieve all records safely ordering by newest creation context
    records = db.query(ApplicationHistory).order_by(ApplicationHistory.created_at.desc()).all()
    return records
