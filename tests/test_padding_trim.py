import numpy as np
import pytest
from PIL import Image

from valid_video.visual_similarity import frames_similarity, trim_padding


def noisy_content(width, height, seed=0):
    """A high-variance 'real content' patch -- stands in for actual video texture."""
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    return Image.fromarray(pixels, mode="RGB")


def pillarboxed(content_image, canvas_width, canvas_height, bar_color=(0, 0, 0)):
    """Paste content_image centered on a larger canvas with solid side bars,
    simulating a 'padded to square' export."""
    canvas = Image.new("RGB", (canvas_width, canvas_height), bar_color)
    x = (canvas_width - content_image.width) // 2
    y = (canvas_height - content_image.height) // 2
    canvas.paste(content_image, (x, y))
    return canvas


def letterboxed(content_image, canvas_width, canvas_height, bar_color=(0, 0, 0)):
    return pillarboxed(content_image, canvas_width, canvas_height, bar_color)


class TestTrimPadding:
    def test_removes_pillarbox_bars(self):
        content = noisy_content(200, 400, seed=1)
        padded = pillarboxed(content, canvas_width=400, canvas_height=400)

        trimmed = trim_padding(padded)

        # Trimmed width should be much closer to the real content width (200)
        # than the padded canvas width (400).
        assert trimmed.width < 300
        assert trimmed.height == padded.height

    def test_removes_letterbox_bars(self):
        content = noisy_content(400, 200, seed=2)
        padded = letterboxed(content, canvas_width=400, canvas_height=400)

        trimmed = trim_padding(padded)

        assert trimmed.height < 300
        assert trimmed.width == padded.width

    def test_image_with_no_padding_is_left_essentially_unchanged(self):
        content = noisy_content(300, 300, seed=3)
        trimmed = trim_padding(content)
        assert trimmed.size == content.size

    def test_fully_uniform_image_falls_back_to_original(self):
        # No detectable "content" at all -- shouldn't crop into oblivion.
        blank = Image.new("RGB", (300, 300), (128, 128, 128))
        trimmed = trim_padding(blank)
        assert trimmed.size == blank.size

    def test_blurred_padding_is_also_trimmed(self):
        # Padding described as "blurred" rather than solid-color -- should
        # still register as low-variance relative to real content.
        content = noisy_content(200, 400, seed=4)
        canvas = Image.new("RGB", (400, 400), (50, 50, 50))
        # simulate slight blur noise in the padding rather than perfectly flat
        rng = np.random.default_rng(99)
        pad_pixels = np.asarray(canvas).copy()
        noise = rng.integers(-3, 4, size=pad_pixels.shape)
        pad_pixels = np.clip(pad_pixels.astype(int) + noise, 0, 255).astype("uint8")
        canvas = Image.fromarray(pad_pixels, mode="RGB")
        x = (400 - content.width) // 2
        canvas.paste(content, (x, 0))

        trimmed = trim_padding(canvas)
        assert trimmed.width < 300


class TestNormalizeFrameHandlesPadding:
    def test_padded_and_cropped_versions_of_same_content_are_now_similar(self):
        # This reproduces the real scenario found in demo testing: a tall
        # frame, one sibling that pillarboxes it to square, another that
        # crops it -- all three should be recognized as highly similar
        # once padding is trimmed before normalization.
        tall_content = noisy_content(200, 400, seed=7)

        # "9:16 original" -- just the content itself, tall
        original = tall_content

        # "1:1 padded" version -- same content, pillarboxed to a square canvas
        padded_square = pillarboxed(tall_content, canvas_width=400, canvas_height=400)

        similarity = frames_similarity(original, padded_square)
        assert similarity > 0.80
