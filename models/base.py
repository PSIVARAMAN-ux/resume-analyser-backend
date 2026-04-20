from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime
import datetime

Base = declarative_base()

class ApplicationHistory(Base):
    __tablename__ = "application_history"

    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String, index=True, nullable=False)
    match_score = Column(Integer, nullable=False)
    cover_letter = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
