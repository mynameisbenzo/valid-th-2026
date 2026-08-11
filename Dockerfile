# ffmpeg (which provides both `ffmpeg` and `ffprobe`) isn't present in
# plain Python runtimes, and Render's native (non-Docker) environment
# doesn't give apt-get access -- so this ships as a Docker web service
# specifically to guarantee ffmpeg is installed.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy just what's needed to install first, so dependency installation
# is cached across rebuilds when only application code changes.
COPY pyproject.toml README.md ./
COPY valid_video ./valid_video

RUN pip install --no-cache-dir -e ".[api]"

# Informational only -- Render assigns the real port via $PORT at runtime,
# read by the CMD below, so this doesn't need to match reality exactly.
EXPOSE 8000

# Render injects $PORT at runtime and expects the service to bind to it --
# it is NOT necessarily 8000, so this must be read at container start,
# not baked in. Shell form (not exec form) is required so $PORT expands.
CMD sh -c "uvicorn valid_video.api:app --host 0.0.0.0 --port ${PORT:-8000}"
