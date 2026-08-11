from valid_video.match_service import find_matches
from valid_video.store import VideoStore


def add(store, filename, ratio_bucket, stem="stem"):
    return store.add(
        filename=filename,
        source=f"/tmp/{filename}",
        width=100,
        height=100,
        aspect_ratio="1:1",
        ratio_bucket=ratio_bucket,
        creative_stem=stem,
        thumbnail_path=f"/tmp/{filename}.thumb.jpg",
    )


def make_compare_fn(similarity_by_pair):
    """similarity_by_pair: dict of frozenset({source_a, source_b}) -> float"""

    def compare_fn(source_a, source_b):
        return similarity_by_pair[frozenset({source_a, source_b})]

    return compare_fn


class TestFindMatches:
    def test_unknown_video_id_returns_none(self):
        store = VideoStore()
        result = find_matches(store, "nonexistent", compare_fn=lambda a, b: 1.0)
        assert result is None

    def test_excluded_other_video_returns_empty_list_not_none(self):
        store = VideoStore()
        queried = add(store, "a.mp4", ratio_bucket="other")
        result = find_matches(store, queried.video_id, compare_fn=lambda a, b: 1.0)
        assert result == []

    def test_never_matches_same_bucket_even_if_visually_similar(self):
        store = VideoStore()
        queried = add(store, "a_9-16.mp4", ratio_bucket="9:16")
        same_bucket = add(store, "b_9-16.mp4", ratio_bucket="9:16")
        compare_fn = make_compare_fn(
            {frozenset({queried.source, same_bucket.source}): 1.0}
        )
        results = find_matches(store, queried.video_id, compare_fn=compare_fn)
        assert results == []

    def test_excludes_other_bucket_candidates(self):
        store = VideoStore()
        queried = add(store, "a_9-16.mp4", ratio_bucket="9:16")
        excluded = add(store, "b_other.mp4", ratio_bucket="other")
        compare_fn = make_compare_fn({frozenset({queried.source, excluded.source}): 1.0})
        results = find_matches(store, queried.video_id, compare_fn=compare_fn)
        assert results == []

    def test_below_threshold_is_not_a_match(self):
        store = VideoStore()
        queried = add(store, "a_9-16.mp4", ratio_bucket="9:16")
        unrelated = add(store, "b_1-1.mp4", ratio_bucket="1:1")
        compare_fn = make_compare_fn({frozenset({queried.source, unrelated.source}): 0.5})
        results = find_matches(store, queried.video_id, compare_fn=compare_fn, threshold=0.8)
        assert results == []

    def test_above_threshold_cross_bucket_is_a_match(self):
        store = VideoStore()
        queried = add(store, "a_9-16.mp4", ratio_bucket="9:16")
        sibling = add(store, "a_1-1.mp4", ratio_bucket="1:1")
        compare_fn = make_compare_fn({frozenset({queried.source, sibling.source}): 0.95})
        results = find_matches(store, queried.video_id, compare_fn=compare_fn, threshold=0.8)
        assert len(results) == 1
        assert results[0].video_id == sibling.video_id
        assert results[0].confidence == 0.95

    def test_results_sorted_descending_by_confidence_and_self_excluded(self):
        store = VideoStore()
        queried = add(store, "a_9-16.mp4", ratio_bucket="9:16")
        sib_1x1 = add(store, "a_1-1.mp4", ratio_bucket="1:1")
        sib_4x5 = add(store, "a_4-5.mp4", ratio_bucket="4:5")
        compare_fn = make_compare_fn(
            {
                frozenset({queried.source, sib_1x1.source}): 0.90,
                frozenset({queried.source, sib_4x5.source}): 0.97,
            }
        )
        results = find_matches(store, queried.video_id, compare_fn=compare_fn, threshold=0.8)
        assert [r.video_id for r in results] == [sib_4x5.video_id, sib_1x1.video_id]
        assert all(r.video_id != queried.video_id for r in results)
