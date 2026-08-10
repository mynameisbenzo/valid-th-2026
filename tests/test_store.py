import pytest

from valid_video.store import VideoStore


def make_record_kwargs(filename="a_9-16.mp4", ratio_bucket="9:16"):
    return dict(
        filename=filename,
        source=f"/tmp/{filename}",
        width=1080,
        height=1920,
        aspect_ratio="9:16",
        ratio_bucket=ratio_bucket,
        creative_stem="a",
    )


def sequential_id_generator(start=10000000):
    n = start
    while True:
        yield str(n)
        n += 1


class TestAdd:
    def test_assigns_a_video_id(self):
        store = VideoStore()
        record = store.add(**make_record_kwargs())
        assert record.video_id is not None
        assert isinstance(record.video_id, str)

    def test_uses_injected_id_generator(self):
        gen = sequential_id_generator(start=42)
        store = VideoStore(id_generator=lambda: next(gen))
        record = store.add(**make_record_kwargs())
        assert record.video_id == "42"

    def test_retries_on_id_collision(self):
        # generator yields a duplicate first, then a fresh one
        ids = iter(["1", "1", "2"])
        store = VideoStore(id_generator=lambda: next(ids))
        first = store.add(**make_record_kwargs(filename="a.mp4"))
        second = store.add(**make_record_kwargs(filename="b.mp4"))
        assert first.video_id == "1"
        assert second.video_id == "2"

    def test_stores_all_given_fields(self):
        store = VideoStore()
        record = store.add(**make_record_kwargs(filename="clip.mp4", ratio_bucket="4:5"))
        assert record.filename == "clip.mp4"
        assert record.ratio_bucket == "4:5"
        assert record.width == 1080
        assert record.height == 1920


class TestGet:
    def test_returns_matching_record(self):
        gen = sequential_id_generator()
        store = VideoStore(id_generator=lambda: next(gen))
        added = store.add(**make_record_kwargs())
        fetched = store.get(added.video_id)
        assert fetched == added

    def test_returns_none_for_unknown_id(self):
        store = VideoStore()
        assert store.get("nonexistent") is None


class TestList:
    def test_returns_all_records(self):
        store = VideoStore()
        store.add(**make_record_kwargs(filename="a.mp4", ratio_bucket="9:16"))
        store.add(**make_record_kwargs(filename="b.mp4", ratio_bucket="1:1"))
        assert len(store.list()) == 2

    def test_filters_by_ratio_bucket(self):
        store = VideoStore()
        store.add(**make_record_kwargs(filename="a.mp4", ratio_bucket="9:16"))
        store.add(**make_record_kwargs(filename="b.mp4", ratio_bucket="1:1"))
        store.add(**make_record_kwargs(filename="c.mp4", ratio_bucket="9:16"))
        results = store.list(ratio_bucket="9:16")
        assert {r.filename for r in results} == {"a.mp4", "c.mp4"}

    def test_empty_store_returns_empty_list(self):
        store = VideoStore()
        assert store.list() == []


class TestDelete:
    def test_removes_existing_record_and_returns_true(self):
        store = VideoStore()
        record = store.add(**make_record_kwargs())
        assert store.delete(record.video_id) is True
        assert store.get(record.video_id) is None

    def test_returns_false_for_unknown_id(self):
        store = VideoStore()
        assert store.delete("nonexistent") is False
