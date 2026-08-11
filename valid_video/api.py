"""FastAPI app: POST /upload, GET /match, GET /videos, DELETE /videos/{id}.

Wires together the pluggable pieces built elsewhere in this package:
  - video_probe.probe_dimensions       (width/height via ffprobe)
  - aspect_ratio.classify_aspect_ratio / simplify_ratio
  - matching.extract_stem              (kept as metadata, not used for matching decisions)
  - visual_matching.compare_videos_visual (the actual match signal)
  - match_service.find_matches         (cross-bucket rule, threshold, ranking)
  - store.VideoStore                   (in-memory; swap for a real DB later)

Everything I/O-adjacent (ffprobe/ffmpeg runners, id generation, upload
directory) is injectable via create_app(), so tests never need real
binaries -- same pattern as the rest of the project.
"""

import os
import subprocess as _subprocess
import uuid
from functools import partial

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from valid_video.aspect_ratio import classify_aspect_ratio, simplify_ratio
from valid_video.match_service import DEFAULT_MATCH_THRESHOLD, find_matches
from valid_video.matching import extract_stem
from valid_video.store import VideoRecord, VideoStore
from valid_video.video_frame_extraction import extract_frame
from valid_video.video_probe import probe_dimensions
from valid_video.visual_matching import compare_videos_visual
from valid_video.web_ui import INDEX_HTML

OTHER_BUCKET = "other"
OTHER_BUCKET_DISPLAY = "Other"


def _display_bucket(ratio_bucket: str) -> str:
    return OTHER_BUCKET_DISPLAY if ratio_bucket == OTHER_BUCKET else ratio_bucket


def _serialize(record: VideoRecord) -> dict:
    return {
        "video_id": record.video_id,
        "width": record.width,
        "height": record.height,
        "aspect_ratio": record.aspect_ratio,
        "ratio_bucket": _display_bucket(record.ratio_bucket),
        "filename": record.filename,
        "thumbnail_url": f"/videos/{record.video_id}/thumbnail" if record.thumbnail_path else None,
    }


def create_app(
    probe_runner=_subprocess.run,
    extract_runner=_subprocess.run,
    id_generator=None,
    upload_dir: str | None = None,
    match_threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> FastAPI:
    app = FastAPI(title="valid-video")

    store = VideoStore(id_generator) if id_generator else VideoStore()
    resolved_upload_dir = upload_dir or "/tmp/valid_video_uploads"
    os.makedirs(resolved_upload_dir, exist_ok=True)

    compare_fn = partial(compare_videos_visual, probe_runner=probe_runner, extract_runner=extract_runner)

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX_HTML

    @app.post("/upload")
    def upload(files: list[UploadFile] = File(...)):
        results = []
        for file in files:
            safe_filename = os.path.basename(file.filename)
            dest_dir = os.path.join(resolved_upload_dir, uuid.uuid4().hex)
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, safe_filename)
            with open(dest_path, "wb") as f:
                f.write(file.file.read())

            width, height = probe_dimensions(dest_path, runner=probe_runner)
            ratio_bucket = classify_aspect_ratio(width, height)
            aspect_ratio = simplify_ratio(width, height)
            creative_stem = extract_stem(safe_filename)

            thumbnail_path = os.path.join(dest_dir, "thumbnail.jpg")
            try:
                extract_frame(
                    dest_path, thumbnail_path, probe_runner=probe_runner, extract_runner=extract_runner
                )
            except Exception:
                # A thumbnail is a nice-to-have -- a corrupt/unreadable video
                # shouldn't fail the whole upload just because we can't
                # preview it. classify/probe above already succeeded, so we
                # still have useful metadata even without a thumbnail.
                thumbnail_path = None

            record = store.add(
                filename=safe_filename,
                source=dest_path,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                ratio_bucket=ratio_bucket,
                creative_stem=creative_stem,
                thumbnail_path=thumbnail_path,
            )
            results.append(_serialize(record))
        return results

    @app.get("/match")
    def match(video_id: str):
        results = find_matches(store, video_id, compare_fn=compare_fn, threshold=match_threshold)
        if results is None:
            raise HTTPException(status_code=404, detail=f"unknown video_id: {video_id!r}")
        return [
            {"video_id": r.video_id, "filename": r.filename, "confidence": r.confidence}
            for r in results
        ]

    @app.get("/videos")
    def list_videos(ratio: str | None = None):
        bucket_filter = None
        if ratio is not None:
            bucket_filter = OTHER_BUCKET if ratio.lower() == "other" else ratio
        records = store.list(ratio_bucket=bucket_filter)
        return [_serialize(r) for r in records]

    @app.get("/videos/{video_id}/thumbnail")
    def get_thumbnail(video_id: str):
        record = store.get(video_id)
        if record is None:
            raise HTTPException(status_code=404, detail=f"unknown video_id: {video_id!r}")
        if not record.thumbnail_path or not os.path.exists(record.thumbnail_path):
            raise HTTPException(status_code=404, detail="thumbnail not available for this video")
        return FileResponse(record.thumbnail_path, media_type="image/jpeg")

    @app.delete("/videos/{video_id}")
    def delete_video(video_id: str):
        if not store.delete(video_id):
            raise HTTPException(status_code=404, detail=f"unknown video_id: {video_id!r}")
        return {"deleted": video_id}

    return app


# Default app instance for `uvicorn valid_video.api:app`. Uses real
# ffprobe/ffmpeg (system PATH) and a local uploads directory -- fine for
# local runs and as the Render deployment entrypoint. Tests use
# create_app() directly with injected fakes instead of this instance.
app = create_app()
