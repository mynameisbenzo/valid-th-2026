"""A local-filesystem stand-in for google.cloud.storage.Client.

Implements the same duck-typed interface pipeline.py expects
(client.bucket(name).blob(name).generate_signed_url(...) and
client.list_blobs(bucket_name)) but backed by a local directory
instead of a real GCS bucket. This lets you run the real pipeline
end-to-end -- real ffprobe, real classification, real matching --
without any cloud credentials.

Not part of the installable valid_video package: this is demo/dev
tooling only. The real production client is google.cloud.storage.Client.
"""

import os
from datetime import timedelta


class LocalBlobRef:
    def __init__(self, name):
        self.name = name


class LocalBlob:
    def __init__(self, directory, blob_name):
        self._path = os.path.join(directory, blob_name)
        if not os.path.isfile(self._path):
            raise FileNotFoundError(self._path)

    def generate_signed_url(self, version: str, expiration: timedelta, method: str) -> str:
        # Real signed URLs are short-lived and remote; here we just
        # hand back the local path so ffprobe can read it directly.
        return self._path


class LocalBucket:
    def __init__(self, directory):
        self._directory = directory

    def blob(self, blob_name):
        return LocalBlob(self._directory, blob_name)


class LocalFilesystemClient:
    """Point this at a directory of sample videos instead of a GCS bucket."""

    def __init__(self, base_directory: str):
        self._base_directory = base_directory

    def bucket(self, bucket_name: str):
        # bucket_name is treated as a subdirectory of base_directory
        return LocalBucket(os.path.join(self._base_directory, bucket_name))

    def list_blobs(self, bucket_name: str):
        directory = os.path.join(self._base_directory, bucket_name)
        return [
            LocalBlobRef(name)
            for name in sorted(os.listdir(directory))
            if name.endswith(".mp4")
        ]
