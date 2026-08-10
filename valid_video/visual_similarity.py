"""Compare video frames visually via perceptual hashing.

Two videos that are the same underlying creative reframed into different
aspect ratios (crop, pad-with-blur, etc.) should produce visually similar
representative frames once normalized to a common shape -- even though
their raw pixel dimensions differ. This module handles that normalization
and the similarity scoring; frame *extraction* from actual video files
lives in video_frame_extraction.py (ffmpeg-based, kept separate so this
module can be tested with synthetic images and no ffmpeg dependency).
"""

import imagehash
import numpy as np
from PIL import Image

DEFAULT_HASH_SIZE = 8
DEFAULT_NORMALIZED_SIZE = 256

# A row/column is considered "padding" if its pixel-value standard
# deviation is below this. Real video content -- textures, edges, subjects
# -- has meaningfully more local variance than a solid or lightly-blurred
# padding bar.
PADDING_VARIANCE_THRESHOLD = 10.0

# If trimming would remove more than this fraction of either dimension,
# something's off (e.g. the whole frame is genuinely flat) -- bail out
# and return the original image rather than crop into near-nothing.
MIN_CONTENT_FRACTION = 0.1


def trim_padding(
    image: Image.Image,
    variance_threshold: float = PADDING_VARIANCE_THRESHOLD,
    min_content_fraction: float = MIN_CONTENT_FRACTION,
) -> Image.Image:
    """Crop out uniform/blurred padding bars, leaving just the real content.

    Detects padding by scanning rows and columns from each edge inward,
    stopping as soon as a row/column's variance clears the threshold
    (i.e. real content starts). Falls back to the original image if the
    detected content region would be implausibly small -- e.g. the frame
    genuinely has no padding, or is itself flat (nothing to trim to).
    """
    grayscale = np.asarray(image.convert("L"), dtype=np.float64)
    height, width = grayscale.shape

    row_std = grayscale.std(axis=1)
    col_std = grayscale.std(axis=0)

    def find_content_bounds(std_by_index: np.ndarray, total: int) -> tuple[int, int]:
        start = 0
        while start < total and std_by_index[start] < variance_threshold:
            start += 1
        end = total - 1
        while end > start and std_by_index[end] < variance_threshold:
            end -= 1
        return start, end

    top, bottom = find_content_bounds(row_std, height)
    left, right = find_content_bounds(col_std, width)

    content_height = bottom - top + 1
    content_width = right - left + 1
    if content_height < height * min_content_fraction or content_width < width * min_content_fraction:
        return image

    return image.crop((left, top, right + 1, bottom + 1))


def normalize_frame(image: Image.Image, size: int = DEFAULT_NORMALIZED_SIZE) -> Image.Image:
    """Trim padding, center-crop to a square, and resize.

    Trimming first means a padded ("blurred edges to fill the canvas")
    sibling and a purely-cropped sibling of the same creative both end up
    showing roughly the same content region at roughly the same scale,
    instead of the padded version looking artificially "zoomed out."
    """
    content = trim_padding(image)
    width, height = content.size
    crop_size = min(width, height)
    left = (width - crop_size) // 2
    top = (height - crop_size) // 2
    cropped = content.crop((left, top, left + crop_size, top + crop_size))
    return cropped.resize((size, size), Image.LANCZOS)


def compute_phash(image: Image.Image, hash_size: int = DEFAULT_HASH_SIZE) -> imagehash.ImageHash:
    """Perceptual hash of a frame, after normalizing it to a square crop."""
    normalized = normalize_frame(image)
    return imagehash.phash(normalized, hash_size=hash_size)


def hash_similarity(
    hash_a: imagehash.ImageHash, hash_b: imagehash.ImageHash, hash_size: int = DEFAULT_HASH_SIZE
) -> float:
    """Convert Hamming distance between two hashes into a [0,1] similarity."""
    total_bits = hash_size * hash_size
    distance = hash_a - hash_b  # imagehash overloads `-` as Hamming distance
    return 1.0 - (distance / total_bits)


def frames_similarity(image_a: Image.Image, image_b: Image.Image) -> float:
    """Visual similarity of two frames, in [0,1]. 1.0 means identical."""
    return hash_similarity(compute_phash(image_a), compute_phash(image_b))
