from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, Security, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.pdf_service import extract_text_from_pdf
from services.ai_service import ai_service
from core.database import get_db
from models.base import ApplicationHistory
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Strict authentication for protected endpoints like /history."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication credentials missing")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload missing subject")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[str]:
    """Optional authentication for /generate so external tools or guest users don't get 401 errors."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, options={"verify_signature": False})
        return payload.get("sub")
    except Exception:
        return None

api_router = APIRouter()

@api_router.get("/")
def read_root():
    return {"message": "Welcome to Resume-to-Job API"}

@api_router.post("/generate")
async def generate_application(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    db: Session = Depends(get_db),
    user_id: Optional[str] = Depends(get_optional_user)
):
    try:
        file_bytes = await resume.read()
        
        # Check if the uploaded file is a PDF or Plain Text
        is_pdf = resume.filename and resume.filename.lower().endswith('.pdf')
        
        if is_pdf or resume.content_type == "application/pdf":
            # Extract text from actual PDF
            resume_text = extract_text_from_pdf(file_bytes)
        else:
            # Fall back to reading plain text directly
            resume_text = file_bytes.decode("utf-8", errors="ignore")
            
        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the provided resume.")
        
        # Call AI Service via Groq
        result_json = await ai_service.generate_tailored_application(
            resume_text=resume_text,
            job_description=job_description
        )
        
        # Save to database if authenticated
        if user_id:
            db_record = ApplicationHistory(
                user_id=user_id,
                job_title=result_json.get("job_title", "Unknown Role"),
                match_score=result_json.get("match_score", 0),
                cover_letter=result_json.get("cover_letter", "")
            )
            db.add(db_record)
            db.commit()
            db.refresh(db_record)
        
        return result_json
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
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
def fetch_history(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    # Retrieve all records isolated by user_id (strictly protected)
    records = db.query(ApplicationHistory).filter(ApplicationHistory.user_id == user_id).order_by(ApplicationHistory.created_at.desc()).all()
    
    return [
        {
            "id": r.id,
            "job_title": r.job_title,
            "match_score": r.match_score,
            "cover_letter": r.cover_letter,
            "created_at": r.created_at.isoformat()
        } for r in records
    ]
