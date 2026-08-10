import os

import numpy as np
from PIL import Image, ImageDraw

from valid_video.visual_matching import compare_videos_visual


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def image_with_shape(width, height, bg_color, shape_color, seed=0):
    # Full-strength texture noise, well clear of the padding-detection
    # variance threshold -- a light perturbation sits too close to that
    # threshold and causes flaky boundary detection between derived crops.
    rng = np.random.default_rng(seed)
    base_color = np.array(Image.new("RGB", (1, 1), bg_color).getpixel((0, 0)))
    noise = rng.integers(-60, 61, size=(height, width, 3))
    pixels = np.clip(base_color + noise, 0, 255).astype("uint8")
    img = Image.fromarray(pixels, mode="RGB")

    draw = ImageDraw.Draw(img)
    cx, cy = width // 2, height // 2
    r = min(width, height) // 4
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=shape_color)
    return img


# Two distinct "video contents" our fake ffmpeg will hand back depending
# on which source URL/path it's asked to extract a frame from.
# "same_creative_b" is genuinely DERIVED from "same_creative_a" (scaled +
# pillarboxed to square), matching the real 9:16 -> 1:1 "blur-pad" export
# relationship -- not just two independently-drawn shapes.
_creative_a = image_with_shape(1080, 1920, "gray", "orange")
_scaled = _creative_a.resize((608, 1080), Image.LANCZOS)
_creative_b = Image.new("RGB", (1080, 1080), tuple(_creative_a.getpixel((0, 0))))
_creative_b.paste(_scaled, ((1080 - 608) // 2, 0))

FRAMES_BY_SOURCE = {
    "same_creative_a.mp4": _creative_a,
    "same_creative_b.mp4": _creative_b,
    "unrelated.mp4": image_with_shape(1080, 1920, "navy", "purple", seed=99),
}


def make_probe_runner():
    def runner(cmd, capture_output, text, timeout):
        return FakeResult(returncode=0, stdout='{"format": {"duration": "4.0"}}')

    return runner


def make_extract_runner():
    def runner(cmd, capture_output, text, timeout):
        source = cmd[cmd.index("-i") + 1]
        output_path = cmd[-1]
        FRAMES_BY_SOURCE[source].save(output_path)
        return FakeResult(returncode=0)

    return runner


class TestCompareVideosVisual:
    def test_same_creative_scores_highly(self):
        similarity = compare_videos_visual(
            "same_creative_a.mp4",
            "same_creative_b.mp4",
            probe_runner=make_probe_runner(),
            extract_runner=make_extract_runner(),
        )
        assert similarity > 0.85

    def test_unrelated_videos_score_lower(self):
        similarity = compare_videos_visual(
            "same_creative_a.mp4",
            "unrelated.mp4",
            probe_runner=make_probe_runner(),
            extract_runner=make_extract_runner(),
        )
        assert similarity < 0.7

    def test_cleans_up_temp_files_after_comparison(self, tmp_path, monkeypatch):
        created_paths = []
        real_extract_runner = make_extract_runner()

        def tracking_runner(cmd, capture_output, text, timeout):
            created_paths.append(cmd[-1])
            return real_extract_runner(cmd, capture_output, text, timeout)

        compare_videos_visual(
            "same_creative_a.mp4",
            "same_creative_b.mp4",
            probe_runner=make_probe_runner(),
            extract_runner=tracking_runner,
        )
        assert len(created_paths) == 2
        for path in created_paths:
            assert not os.path.exists(path)
