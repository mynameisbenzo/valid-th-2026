"""Probe video width/height via ffprobe, pointed directly at a URL.

ffprobe can read just the header atoms of a remote file over HTTP(S)
without downloading the whole thing, so we pass the GCS signed URL
straight in rather than downloading the video first.

The subprocess runner is injectable (`runner=subprocess.run` by default)
so tests never need a real ffprobe binary or a real video file.
"""

import json
import subprocess as _subprocess

DEFAULT_TIMEOUT_SECONDS = 30


def probe_dimensions(source: str, runner=_subprocess.run, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> tuple[int, int]:
    """Return (width, height) of the first video stream found in `source`.

    `source` may be a local path or a remote URL (e.g. a GCS signed URL).
    Raises RuntimeError if ffprobe itself fails or times out, and
    ValueError if its output can't be parsed or contains no video stream.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        source,
    ]

    try:
        result = runner(cmd, capture_output=True, text=True, timeout=timeout)
    except _subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffprobe timed out probing {source!r}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffprobe was not found. Install ffmpeg and make sure it's on your "
            "PATH (e.g. `brew install ffmpeg` on macOS, `apt install ffmpeg` "
            "on Debian/Ubuntu, or download a build from https://ffmpeg.org/download.html "
            "on Windows and add its `bin` folder to PATH)."
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed for {source!r} (exit {result.returncode}): {result.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"could not parse ffprobe output for {source!r}: {exc}") from exc

    streams = data.get("streams", [])
    if not streams:
        raise ValueError(f"no video stream found in {source!r}")

    first_stream = streams[0]
    return (first_stream["width"], first_stream["height"])
