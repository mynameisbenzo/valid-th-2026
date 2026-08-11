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

## Deploying to Render

This ships as a Docker web service specifically because Render's plain
Python runtime doesn't include `ffmpeg`/`ffprobe`, and its native
(non-Docker) build environment doesn't allow installing system packages.
The included `Dockerfile` installs `ffmpeg` via `apt-get` to guarantee
it's present.

Everything is in-memory (no database) -- uploaded videos and their
records live only for the life of the running instance, which is
expected on Render's free plan (the instance spins down after
inactivity, and redeploys reset state).

**Steps:**

1. Push this repository to GitHub (or GitLab).
2. In the Render dashboard: **New +** -> **Blueprint**, then point it at
   your repo. Render will detect `render.yaml` and configure the service
   automatically (Docker environment, free plan, health check on
   `/videos`). Alternatively, **New +** -> **Web Service**, select
   **Docker** as the environment, and point `dockerfilePath` at
   `./Dockerfile` manually.
3. Wait for the build to finish (installing `ffmpeg` adds a little time
   on the first build; cached on subsequent ones).
4. Visit the assigned `https://<your-service>.onrender.com/` URL -- same
   drag-and-drop console as running locally.

**Known free-tier caveats:**
- The instance spins down after ~15 minutes of inactivity; the first
  request after that ("cold start") can take 30-60+ seconds while it
  restarts -- this is normal, not a bug.
- Free web services have a request timeout (Render's default, not
  something this app configures); very large video files or many
  simultaneous `/match` comparisons could theoretically hit it. Not
  expected to be an issue for typical demo-sized files.
- Uploaded videos are written to a temp directory on local disk before
  probing/hashing -- ephemeral, cleared on restart, consistent with the
  in-memory design above.

## CI/CD: tests gate deployment

`.github/workflows/ci.yml` runs the full test suite on every push and
pull request. On `main`, a deploy to Render is triggered **only if tests
pass** -- a failing push never goes live. This works via Render's Deploy
Hook (a secret URL that starts a deploy when hit) rather than Render's
default "auto-deploy on every push," which would deploy regardless of
test results and defeat the gate.

**One-time setup (after the Render service above already exists):**

1. **Get the Deploy Hook URL**: in the Render dashboard, open the
   `valid-video` service -> **Settings** -> scroll to **Deploy Hook** ->
   copy the URL shown there.
2. **Add it as a GitHub secret**: in your GitHub repo, go to **Settings**
   -> **Secrets and variables** -> **Actions** -> **New repository
   secret**. Name it `RENDER_DEPLOY_HOOK_URL`, paste the URL as the value.
3. **Confirm auto-deploy is off**: `render.yaml` already sets
   `autoDeploy: false`, but if the service was created before this was
   added, double check in the Render dashboard under **Settings** ->
   **Build & Deploy** -> **Auto-Deploy** is set to **No**.

After that, every push to `main` runs the tests; if they pass, the
`deploy` job calls the Deploy Hook and Render starts a new deploy. Pull
requests only run tests -- they never deploy, even if they target `main`.
