"""Orchestrates the full flow: list bucket -> sign -> probe -> classify -> match.

This is the only module that knows about all four building blocks. Each
of those blocks is independently tested and mockable; here we just wire
them together and handle the "one bad video shouldn't sink the whole
report" bookkeeping.
"""

from datetime import timedelta

from valid_video.aspect_ratio import CANONICAL_RATIOS, classify_aspect_ratio
from valid_video.gcs_signing import DEFAULT_EXPIRATION, generate_signed_urls_for_files
from valid_video.matching import group_by_stem
from valid_video.video_probe import probe_dimensions

ALL_BUCKET_LABELS = list(CANONICAL_RATIOS.keys()) + ["other"]


def _list_blob_names(client, bucket_name: str) -> list[str]:
    return [blob.name for blob in client.list_blobs(bucket_name)]


def build_report(
    client,
    bucket_name: str,
    probe_runner=None,
    expiration: timedelta = DEFAULT_EXPIRATION,
) -> dict:
    """Build the full bucketing + matching report for a GCS bucket.

    Returns a dict with:
      - "videos": {filename: {signed_url, width, height, aspect_ratio}}
      - "buckets": {"9:16": [...], "1:1": [...], "4:5": [...], "16:9": [...], "other": [...]}
      - "matches": {creative_stem: [filenames]} -- only stems with 2+ files
      - "errors": {filename: error_message} -- signing or probing failures
    """
    filenames = _list_blob_names(client, bucket_name)

    videos: dict[str, dict] = {}
    buckets: dict[str, list[str]] = {label: [] for label in ALL_BUCKET_LABELS}
    errors: dict[str, str] = {}

    signed_urls = generate_signed_urls_for_files(client, bucket_name, filenames, expiration)
    for filename in filenames:
        if filename not in signed_urls:
            errors[filename] = "failed to generate signed URL"
            continue

    probe_kwargs = {"runner": probe_runner} if probe_runner is not None else {}

    for filename, signed_url in signed_urls.items():
        try:
            width, height = probe_dimensions(signed_url, **probe_kwargs)
        except (RuntimeError, ValueError) as exc:
            errors[filename] = str(exc)
            continue

        ratio = classify_aspect_ratio(width, height)
        videos[filename] = {
            "signed_url": signed_url,
            "width": width,
            "height": height,
            "aspect_ratio": ratio,
        }
        buckets[ratio].append(filename)

    stem_groups = group_by_stem(list(videos.keys()))
    matches = {stem: files for stem, files in stem_groups.items() if len(files) > 1}

    return {
        "videos": videos,
        "buckets": buckets,
        "matches": matches,
        "errors": errors,
    }
