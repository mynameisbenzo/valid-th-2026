"""Extract a representative frame from a video via ffmpeg, pointed at a
local path or a remote URL (e.g. a GCS signed URL) -- same "point ffmpeg
tools directly at the URL" approach as video_probe.py.

Both the duration probe (ffprobe) and the frame extraction (ffmpeg) use
injectable runners so tests never need real binaries or real video files.
"""

import json
import subprocess as _subprocess

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_TIMESTAMP_FRACTION = 0.5


def probe_duration(source: str, runner=_subprocess.run, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> float:
    """Return the duration of `source` in seconds via ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        source,
    ]
    try:
        result = runner(cmd, capture_output=True, text=True, timeout=timeout)
    except _subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffprobe timed out probing duration of {source!r}") from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed to get duration for {source!r} "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise ValueError(f"could not parse duration for {source!r}: {exc}") from exc


def extract_frame(
    source: str,
    output_path: str,
    timestamp_fraction: float = DEFAULT_TIMESTAMP_FRACTION,
    probe_runner=_subprocess.run,
    extract_runner=_subprocess.run,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Extract a single representative frame from `source` to `output_path`.

    The frame is taken at `timestamp_fraction` of the way through the
    video (0.5 = midpoint by default), which tends to avoid intro/outro
    title cards that might differ between otherwise-identical creatives.
    """
    duration = probe_duration(source, runner=probe_runner, timeout=timeout)
    timestamp = round(duration * timestamp_fraction, 2)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(timestamp),
        "-i", source,
        "-frames:v", "1",
        "-q:v", "2",
        output_path,
    ]

    try:
        result = extract_runner(cmd, capture_output=True, text=True, timeout=timeout)
    except _subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffmpeg timed out extracting a frame from {source!r}") from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed to extract a frame from {source!r} "
            f"(exit {result.returncode}): {result.stderr.strip()}"
        )
