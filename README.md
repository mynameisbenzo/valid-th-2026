# valid-video

Buckets MP4s into canonical aspect ratios (9:16, 1:1, 4:5, 16:9, or "Other")
and detects which videos are the same underlying creative reframed across
different ratios, using real visual similarity (perceptual hashing) rather
than filename guessing.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[api,dev]"
```

Requires `ffmpeg`/`ffprobe` on your system PATH (`brew install ffmpeg` /
`apt install ffmpeg`).

## Run the tests

```bash
pytest -v
```

## Run the API

```bash
uvicorn valid_video.api:app --reload --port 8000
```

Then visit `http://127.0.0.1:8000/docs` for interactive Swagger docs, or see
`demo/run_demo.py` for a scripted example against local sample videos.

## Endpoints

- `POST /upload` — upload one or more MP4 files (multipart, field name `files`)
- `GET /match?video_id=<id>` — cross-bucket same-creative matches for a video
- `GET /videos[?ratio=9:16]` — list uploaded videos, optionally filtered
- `DELETE /videos/<id>` — remove an uploaded video

## Architecture

Every external dependency (the GCS client, ffprobe/ffmpeg, ID generation)
is duck-typed/injectable, so the test suite runs without real credentials,
binaries, or video files. See individual module docstrings for details.
