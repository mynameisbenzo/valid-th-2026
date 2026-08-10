from datetime import timedelta

import pytest

from valid_video.gcs_signing import generate_signed_url, generate_signed_urls_for_files


class FakeBlob:
    """Stand-in for google.cloud.storage.Blob -- records call args."""

    def __init__(self, bucket_name, blob_name):
        self.bucket_name = bucket_name
        self.blob_name = blob_name
        self.last_call = None

    def generate_signed_url(self, version, expiration, method):
        self.last_call = {"version": version, "expiration": expiration, "method": method}
        return f"https://signed.example.com/{self.bucket_name}/{self.blob_name}?exp={expiration}"


class FakeBucket:
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.blobs_created = {}

    def blob(self, blob_name):
        blob = FakeBlob(self.bucket_name, blob_name)
        self.blobs_created[blob_name] = blob
        return blob


class FakeClient:
    """Stand-in for google.cloud.storage.Client."""

    def __init__(self):
        self.buckets = {}

    def bucket(self, bucket_name):
        if bucket_name not in self.buckets:
            self.buckets[bucket_name] = FakeBucket(bucket_name)
        return self.buckets[bucket_name]


class TestGenerateSignedUrl:
    def test_returns_url_from_client(self):
        client = FakeClient()
        url = generate_signed_url(client, "my-bucket", "campaign123_9-16.mp4")
        assert url == (
            "https://signed.example.com/my-bucket/campaign123_9-16.mp4"
            "?exp=" + str(timedelta(minutes=15))
        )

    def test_defaults_to_v4_get_15_minutes(self):
        client = FakeClient()
        generate_signed_url(client, "my-bucket", "clip.mp4")
        blob = client.buckets["my-bucket"].blobs_created["clip.mp4"]
        assert blob.last_call == {
            "version": "v4",
            "expiration": timedelta(minutes=15),
            "method": "GET",
        }

    def test_custom_expiration_is_passed_through(self):
        client = FakeClient()
        generate_signed_url(
            client, "my-bucket", "clip.mp4", expiration=timedelta(minutes=5)
        )
        blob = client.buckets["my-bucket"].blobs_created["clip.mp4"]
        assert blob.last_call["expiration"] == timedelta(minutes=5)

    def test_zero_or_negative_expiration_raises(self):
        client = FakeClient()
        with pytest.raises(ValueError):
            generate_signed_url(
                client, "my-bucket", "clip.mp4", expiration=timedelta(seconds=0)
            )


class TestGenerateSignedUrlsForFiles:
    def test_returns_mapping_of_filename_to_url(self):
        client = FakeClient()
        filenames = ["a_9-16.mp4", "a_1-1.mp4"]
        result = generate_signed_urls_for_files(client, "my-bucket", filenames)
        assert set(result.keys()) == set(filenames)
        assert result["a_9-16.mp4"].startswith("https://signed.example.com/my-bucket/a_9-16.mp4")

    def test_empty_file_list_returns_empty_dict(self):
        client = FakeClient()
        assert generate_signed_urls_for_files(client, "my-bucket", []) == {}

    def test_one_bad_filename_does_not_prevent_others_from_being_signed(self):
        # Simulate a client that raises for one specific blob (e.g. it doesn't
        # exist in the bucket). The batch helper should skip it, not abort.
        class FlakyClient(FakeClient):
            def bucket(self, bucket_name):
                bucket = super().bucket(bucket_name)
                original_blob = bucket.blob

                def blob(blob_name):
                    if blob_name == "missing.mp4":
                        raise FileNotFoundError(blob_name)
                    return original_blob(blob_name)

                bucket.blob = blob
                return bucket

        client = FlakyClient()
        result = generate_signed_urls_for_files(
            client, "my-bucket", ["missing.mp4", "present.mp4"]
        )
        assert "missing.mp4" not in result
        assert "present.mp4" in result
