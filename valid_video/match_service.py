"""Decide which stored videos match a queried video, and rank them.

This module knows about buckets and the cross-bucket-only rule, but not
about how similarity is actually computed -- that's injected as
`compare_fn(source_a, source_b) -> float`, so this stays fast to test
and swappable (visual similarity today, could add audio later).
"""

from dataclasses import dataclass

OTHER_BUCKET = "other"
DEFAULT_MATCH_THRESHOLD = 0.80


@dataclass
class MatchResult:
    video_id: str
    filename: str
    confidence: float


def find_matches(
    store,
    video_id: str,
    compare_fn,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> list[MatchResult] | None:
    """Return ranked matches for `video_id`, or None if the id is unknown.

    - Unknown video_id -> None (caller should respond 404)
    - Known but excluded ("other" bucket) video -> [] (excluded videos never match)
    - Otherwise -> matches in *other* buckets only, above `threshold`,
      sorted by confidence descending. Empty list if none clear the bar.
    """
    query = store.get(video_id)
    if query is None:
        return None

    if query.ratio_bucket == OTHER_BUCKET:
        return []

    results: list[MatchResult] = []
    for candidate in store.list():
        if candidate.video_id == query.video_id:
            continue
        if candidate.ratio_bucket == OTHER_BUCKET:
            continue
        if candidate.ratio_bucket == query.ratio_bucket:
            continue

        similarity = compare_fn(query.source, candidate.source)
        if similarity >= threshold:
            results.append(
                MatchResult(
                    video_id=candidate.video_id,
                    filename=candidate.filename,
                    confidence=round(similarity, 2),
                )
            )

    results.sort(key=lambda r: r.confidence, reverse=True)
    return results
