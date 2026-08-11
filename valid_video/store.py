"""In-memory storage for uploaded video records.

Pluggable id_generator so tests get deterministic IDs, same pattern used
throughout this project (gcs_signing's client, video_probe's runner, etc).
Swapping this for a real database later means writing a class with the
same add/get/list/delete interface -- the API layer doesn't need to change.
"""

import random
from dataclasses import dataclass

MAX_ID_GENERATION_ATTEMPTS = 10


def _default_id_generator() -> str:
    return str(random.randint(10_000_000, 99_999_999))


@dataclass(frozen=True)
class VideoRecord:
    video_id: str
    filename: str
    source: str  # local path or URL used to probe/extract frames from
    width: int
    height: int
    aspect_ratio: str  # exact reduced fraction, e.g. "7:3"
    ratio_bucket: str  # canonical bucket: "9:16" | "1:1" | "4:5" | "16:9" | "other"
    creative_stem: str  # filename-derived grouping key (kept for reference/fallback)
    thumbnail_path: str | None  # local path to the extracted representative frame (JPEG), or None if extraction failed


class VideoStore:
    def __init__(self, id_generator=_default_id_generator):
        self._records: dict[str, VideoRecord] = {}
        self._id_generator = id_generator

    def add(
        self,
        filename: str,
        source: str,
        width: int,
        height: int,
        aspect_ratio: str,
        ratio_bucket: str,
        creative_stem: str,
        thumbnail_path: str,
    ) -> VideoRecord:
        video_id = self._generate_unique_id()
        record = VideoRecord(
            video_id=video_id,
            filename=filename,
            source=source,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            ratio_bucket=ratio_bucket,
            creative_stem=creative_stem,
            thumbnail_path=thumbnail_path,
        )
        self._records[video_id] = record
        return record

    def get(self, video_id: str) -> VideoRecord | None:
        return self._records.get(video_id)

    def list(self, ratio_bucket: str | None = None) -> list[VideoRecord]:
        records = list(self._records.values())
        if ratio_bucket is not None:
            records = [r for r in records if r.ratio_bucket == ratio_bucket]
        return records

    def delete(self, video_id: str) -> bool:
        return self._records.pop(video_id, None) is not None

    def _generate_unique_id(self) -> str:
        for _ in range(MAX_ID_GENERATION_ATTEMPTS):
            candidate = self._id_generator()
            if candidate not in self._records:
                return candidate
        raise RuntimeError("could not generate a unique video_id after several attempts")
