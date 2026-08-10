import uuid
from sqlalchemy import Column, String, Float, Boolean, JSON, DateTime, func
from database import Base

class VideoValidationLog(Base):
    __tablename__ = "validation_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    campaign_id = Column(String, nullable=True)
    is_valid = Column(Boolean, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    aspect_ratio = Column(String, nullable=True)
    errors = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())