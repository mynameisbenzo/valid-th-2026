from PIL import Image, ImageDraw
import numpy as np
import numpy as np

from valid_video.visual_similarity import (
    compute_phash,
    frames_similarity,
    normalize_frame,
    trim_padding,
)


def solid_color_image(width, height, color):
    return Image.new("RGB", (width, height), color)


def image_with_shape(width, height, bg_color, shape_color, seed=0):
    """A textured background with a shape drawn near the center -- stands
    in for 'a video frame with a subject in the middle.' Uses full-strength
    random texture (not just a light perturbation) so it sits well clear
    of the padding-detection variance threshold, avoiding flaky boundary
    detection right at the edge of that threshold."""
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


class TestNormalizeFrame:
    def test_output_is_square(self):
        img = solid_color_image(1080, 1920, "blue")
        normalized = normalize_frame(img, size=256)
        assert normalized.size == (256, 256)

    def test_wide_image_is_also_normalized_to_square(self):
        img = solid_color_image(1920, 1080, "red")
        normalized = normalize_frame(img, size=256)
        assert normalized.size == (256, 256)

    def test_center_crop_preserves_center_content(self):
        # A shape centered in a wide canvas should still be centered
        # (and present) after a center-crop + resize to square.
        img = image_with_shape(1920, 1080, "black", "white")
        normalized = normalize_frame(img, size=256)
        center_pixel = normalized.getpixel((128, 128))
        # center pixel should be close to white (the shape), not black (bg)
        assert sum(center_pixel) > 400  # white-ish, not black-ish


class TestFramesSimilarity:
    def test_identical_images_are_perfectly_similar(self):
        img = image_with_shape(1080, 1920, "black", "white")
        assert frames_similarity(img, img) == 1.0

    def test_same_subject_different_padding_is_highly_similar(self):
        # simulates the 9:16 -> 1:1 "pad with blur" relationship: the
        # square version is DERIVED from the tall one (scaled down +
        # pillarboxed), not independently drawn -- a true representation
        # of "same content, different export."
        tall = image_with_shape(1080, 1920, "gray", "orange")
        scaled_content = tall.resize((608, 1080), Image.LANCZOS)
        square = Image.new("RGB", (1080, 1080), tall.getpixel((0, 0)))
        square.paste(scaled_content, ((1080 - 608) // 2, 0))

        similarity = frames_similarity(tall, square)
        assert similarity > 0.80

    def test_same_subject_different_reframing_is_reasonably_similar(self):
        # simulates 9:16 -> 4:5 "reframe" relationship: the medium version
        # is a genuine center-crop of the tall one, not independently drawn.
        tall = image_with_shape(1080, 1920, "gray", "orange")
        medium = tall.crop((0, (1920 - 1350) // 2, 1080, (1920 - 1350) // 2 + 1350))
        similarity = frames_similarity(tall, medium)
        assert similarity > 0.85

    def test_unrelated_content_has_low_similarity(self):
        subject_a = image_with_shape(1080, 1920, "black", "white")
        subject_b = solid_color_image(1080, 1920, "green")
        similarity = frames_similarity(subject_a, subject_b)
        assert similarity < 0.7

    def test_similarity_is_symmetric(self):
        img_a = image_with_shape(1080, 1920, "navy", "yellow")
        img_b = image_with_shape(1080, 1080, "navy", "yellow")
        assert frames_similarity(img_a, img_b) == frames_similarity(img_b, img_a)

    def test_similarity_is_bounded_between_zero_and_one(self):
        img_a = image_with_shape(1080, 1920, "black", "white")
        img_b = solid_color_image(1080, 1920, "red")
        similarity = frames_similarity(img_a, img_b)
        assert 0.0 <= similarity <= 1.0


class TestComputePhash:
    def test_returns_consistent_hash_for_same_image(self):
        img = image_with_shape(1080, 1920, "black", "white")
        assert compute_phash(img) == compute_phash(img)


def noisy_texture(width, height, seed=0):
    """A textured (high local-variance) RGB image -- stands in for real
    video content, as opposed to flat/blurred padding."""
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(height, width, 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


def pillarboxed_image(bar_width, content_width, height, bar_color=(0, 0, 0), seed=0):
    """content flanked by solid bars on left/right -- e.g. a 9:16 video
    padded to fit a square canvas."""
    total_width = bar_width * 2 + content_width
    img = Image.new("RGB", (total_width, height), bar_color)
    content = noisy_texture(content_width, height, seed=seed)
    img.paste(content, (bar_width, 0))
    return img


def letterboxed_image(bar_height, content_height, width, bar_color=(0, 0, 0), seed=0):
    """content flanked by solid bars on top/bottom."""
    total_height = bar_height * 2 + content_height
    img = Image.new("RGB", (width, total_height), bar_color)
    content = noisy_texture(width, content_height, seed=seed)
    img.paste(content, (0, bar_height))
    return img


def blurred_pillarboxed_image(bar_width, content_width, height, seed=0):
    """Like pillarboxed_image, but the bars are a blurred/smooth gradient
    rather than a perfectly flat color -- matches the FAQ's description
    of '9:16 video with the edges blurred to pad it square'."""
    from PIL import ImageFilter

    total_width = bar_width * 2 + content_width
    img = Image.new("RGB", (total_width, height), (128, 128, 128))
    content = noisy_texture(content_width, height, seed=seed)
    img.paste(content, (bar_width, 0))
    # blur just the bar regions heavily by blurring a copy and pasting
    # the blurred bars back over the original bar areas
    blurred = img.filter(ImageFilter.GaussianBlur(radius=15))
    img.paste(blurred.crop((0, 0, bar_width, height)), (0, 0))
    right_start = bar_width + content_width
    img.paste(blurred.crop((right_start, 0, total_width, height)), (right_start, 0))
    return img


class TestTrimPadding:
    def test_removes_pillarbox_bars(self):
        img = pillarboxed_image(bar_width=50, content_width=200, height=100)
        trimmed = trim_padding(img)
        # trimmed width should be close to the content region, not the full 300px
        assert trimmed.size[0] < 250
        assert trimmed.size[0] > 150

    def test_removes_letterbox_bars(self):
        img = letterboxed_image(bar_height=50, content_height=200, width=100)
        trimmed = trim_padding(img)
        assert trimmed.size[1] < 250
        assert trimmed.size[1] > 150

    def test_removes_blurred_pillarbox_bars(self):
        img = blurred_pillarboxed_image(bar_width=50, content_width=200, height=100)
        trimmed = trim_padding(img)
        assert trimmed.size[0] < 250
        assert trimmed.size[0] > 150

    def test_full_bleed_content_is_left_largely_unchanged(self):
        img = noisy_texture(300, 100, seed=1)
        trimmed = trim_padding(img)
        # should not have chopped off much of a full-bleed textured image
        assert trimmed.size[0] > 270
        assert trimmed.size[1] > 90

    def test_fully_uniform_image_is_not_cropped_to_nothing(self):
        img = Image.new("RGB", (200, 200), (50, 50, 50))
        trimmed = trim_padding(img)
        # degenerate case: no content region detectable -- fall back to original
        assert trimmed.size == (200, 200)

    def test_trimming_improves_cross_padding_similarity(self):
        # This is the actual FAQ scenario: same content, one version padded
        # to a square with blurred bars. Similarity after trimming+normalizing
        # should be much higher than without trimming.
        content_seed = 7
        tall_content = noisy_texture(200, 400, seed=content_seed)
        padded_square = blurred_pillarboxed_image(bar_width=100, content_width=200, height=400, seed=content_seed)

        similarity = frames_similarity(tall_content, padded_square)
        assert similarity > 0.7
