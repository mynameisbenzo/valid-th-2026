import json
from datetime import timedelta

import pytest

from valid_video.pipeline import build_report


class FakeBlobName:
    """What client.list_blobs(...) yields in the real SDK: objects with .name"""

    def __init__(self, name):
        self.name = name


class FakeBlob:
    def __init__(self, bucket_name, blob_name):
        self.bucket_name = bucket_name
        self.blob_name = blob_name

    def generate_signed_url(self, version, expiration, method):
        return f"https://signed.example.com/{self.bucket_name}/{self.blob_name}"


class FakeBucket:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name

    def blob(self, blob_name):
        if blob_name == "corrupt_9-16.mp4":
            raise FileNotFoundError(blob_name)
        return FakeBlob(self.bucket_name, blob_name)


class FakeClient:
    def __init__(self, filenames):
        self._filenames = filenames

    def bucket(self, bucket_name):
        return FakeBucket(bucket_name)

    def list_blobs(self, bucket_name):
        return [FakeBlobName(name) for name in self._filenames]


# Maps signed URL -> (width, height), used by the fake ffprobe runner below.
DIMENSIONS_BY_FILENAME = {
    "campaign123_9-16.mp4": (1080, 1920),
    "campaign123_1-1.mp4": (1080, 1080),
    "campaign123_4-5.mp4": (1080, 1350),
    "campaign456_16-9.mp4": (1920, 1080),
    "weird_ratio.mp4": (1000, 333),  # doesn't fit any canonical bucket -> "other"
}


def make_probe_runner(fails_for=()):
    def runner(cmd, capture_output, text, timeout):
        url = cmd[-1]
        # our fake signed urls look like https://signed.example.com/{bucket}/{filename}
        filename = url.rsplit("/", 1)[-1]

        class Result:
            pass

        result = Result()
        if filename in fails_for:
            result.returncode = 1
            result.stdout = ""
            result.stderr = "simulated ffprobe failure"
            return result

        width, height = DIMENSIONS_BY_FILENAME[filename]
        result.returncode = 0
        result.stdout = json.dumps({"streams": [{"width": width, "height": height}]})
        result.stderr = ""
        return result

    return runner


class TestBuildReport:
    def test_classifies_each_video_into_its_aspect_ratio_bucket(self):
        filenames = list(DIMENSIONS_BY_FILENAME.keys())
        client = FakeClient(filenames)
        report = build_report(client, "my-bucket", probe_runner=make_probe_runner())

        assert report["buckets"]["9:16"] == ["campaign123_9-16.mp4"]
        assert report["buckets"]["1:1"] == ["campaign123_1-1.mp4"]
        assert report["buckets"]["4:5"] == ["campaign123_4-5.mp4"]
        assert report["buckets"]["16:9"] == ["campaign456_16-9.mp4"]
        assert report["buckets"]["other"] == ["weird_ratio.mp4"]

    def test_groups_same_creative_across_ratios_as_a_match(self):
        filenames = list(DIMENSIONS_BY_FILENAME.keys())
        client = FakeClient(filenames)
        report = build_report(client, "my-bucket", probe_runner=make_probe_runner())

        assert report["matches"]["campaign123"] == [
            "campaign123_9-16.mp4",
            "campaign123_1-1.mp4",
            "campaign123_4-5.mp4",
        ]
        # campaign456 and weird_ratio are singletons -- not "matches"
        assert "campaign456" not in report["matches"]
        assert "weird_ratio" not in report["matches"]

    def test_each_video_entry_has_signed_url_and_dimensions(self):
        filenames = ["campaign123_9-16.mp4"]
        client = FakeClient(filenames)
        report = build_report(client, "my-bucket", probe_runner=make_probe_runner())

        entry = report["videos"]["campaign123_9-16.mp4"]
        assert entry["signed_url"] == "https://signed.example.com/my-bucket/campaign123_9-16.mp4"
        assert entry["width"] == 1080
        assert entry["height"] == 1920
        assert entry["aspect_ratio"] == "9:16"

    def test_probe_failure_is_recorded_as_error_not_a_crash(self):
        filenames = ["campaign123_9-16.mp4", "campaign123_1-1.mp4"]
        client = FakeClient(filenames)
        runner = make_probe_runner(fails_for=["campaign123_1-1.mp4"])
        report = build_report(client, "my-bucket", probe_runner=runner)

        assert "campaign123_1-1.mp4" in report["errors"]
        assert "campaign123_9-16.mp4" not in report["errors"]
        # the failed video shouldn't appear in any ratio bucket
        assert "campaign123_1-1.mp4" not in report["buckets"]["1:1"]

    def test_signing_failure_is_recorded_as_error_not_a_crash(self):
        filenames = ["corrupt_9-16.mp4", "campaign123_9-16.mp4"]
        client = FakeClient(filenames)
        report = build_report(client, "my-bucket", probe_runner=make_probe_runner())

        assert "corrupt_9-16.mp4" in report["errors"]
        assert report["videos"].get("corrupt_9-16.mp4") is None

    def test_empty_bucket_returns_empty_report(self):
        client = FakeClient([])
        report = build_report(client, "my-bucket", probe_runner=make_probe_runner())

        assert report["videos"] == {}
        assert report["matches"] == {}
        assert all(bucket == [] for bucket in report["buckets"].values())

    def test_custom_expiration_is_used_for_signing(self):
        filenames = ["campaign123_9-16.mp4"]
        client = FakeClient(filenames)
        # doesn't raise, and signed_url still present -- confirms the param flows through
        report = build_report(
            client,
            "my-bucket",
            probe_runner=make_probe_runner(),
            expiration=timedelta(minutes=5),
        )
        assert "signed_url" in report["videos"]["campaign123_9-16.mp4"]
