import shutil
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, Base, get_db
from models import VideoValidationLog
from valid_video.pipeline import validate_video  # Core library logic

app = FastAPI(title="Valid Video API")

# Initialize DB tables on startup
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.post("/api/v1/validate")
async def validate_video_endpoint(
    file: UploadFile = File(...),
    campaign_id: str = Form(None),
    max_duration: float = Form(30.0),
    db: AsyncSession = Depends(get_db)
):
    # Save uploaded file temporarily for ffprobe inspection
    suffix = Path(file.filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Run validation pipeline from valid_video package
        report = validate_video(
            video_path=tmp_path,
            expected_campaign_id=campaign_id,
            max_duration_seconds=max_duration
        )

        # Log result to Render PostgreSQL
        log_entry = VideoValidationLog(
            filename=file.filename,
            campaign_id=campaign_id,
            is_valid=report.is_valid,
            duration_seconds=report.metadata.get("duration"),
            aspect_ratio=report.metadata.get("aspect_ratio"),
            errors=report.errors
        )
        db.add(log_entry)
        await db.commit()

        return {
            "status": "success",
            "is_valid": report.is_valid,
            "errors": report.errors,
            "metadata": report.metadata
        }

    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)