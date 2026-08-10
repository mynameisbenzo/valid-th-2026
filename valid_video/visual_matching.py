"""Compare two videos' visual content: extract a representative frame
from each and score their similarity via perceptual hashing.

This is the function the API layer calls once per candidate pair when
answering GET /match -- it's deliberately not aware of buckets, stems,
or the video store; those concerns stay in the API layer.
"""

import os
import subprocess as _subprocess
import tempfile

from PIL import Image

from valid_video.video_frame_extraction import extract_frame
from valid_video.visual_similarity import frames_similarity


def compare_videos_visual(
    source_a: str,
    source_b: str,
    probe_runner=_subprocess.run,
    extract_runner=_subprocess.run,
) -> float:
    """Return visual similarity of two videos' representative frames, in [0,1]."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        frame_a_path = os.path.join(tmp_dir, "frame_a.jpg")
        frame_b_path = os.path.join(tmp_dir, "frame_b.jpg")

        extract_frame(source_a, frame_a_path, probe_runner=probe_runner, extract_runner=extract_runner)
        extract_frame(source_b, frame_b_path, probe_runner=probe_runner, extract_runner=extract_runner)

        with Image.open(frame_a_path) as image_a, Image.open(frame_b_path) as image_b:
            return frames_similarity(image_a, image_b)
