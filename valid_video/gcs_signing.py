"""Pluggable V4 signed URL generation for private GCS objects.

This module has no hard dependency on the `google-cloud-storage` SDK.
It works against any object satisfying the minimal duck-typed interface
used here: `client.bucket(name).blob(name).generate_signed_url(...)`.
That means:
  - Tests inject a lightweight fake (no network, no credentials needed).
  - Production wires in a real `google.cloud.storage.Client()`.
Swapping one for the other requires no changes to this module.
"""

from datetime import timedelta
from typing import Protocol

DEFAULT_EXPIRATION = timedelta(minutes=15)


class SigningBlob(Protocol):
    def generate_signed_url(self, version: str, expiration: timedelta, method: str) -> str: ...


class SigningBucket(Protocol):
    def blob(self, blob_name: str) -> SigningBlob: ...


class SigningClient(Protocol):
    def bucket(self, bucket_name: str) -> SigningBucket: ...


def generate_signed_url(
    client: SigningClient,
    bucket_name: str,
    blob_name: str,
    expiration: timedelta = DEFAULT_EXPIRATION,
) -> str:
    """Generate a short-lived V4 signed GET URL for a single blob."""
    if expiration <= timedelta(0):
        raise ValueError(f"expiration must be positive, got {expiration}")

    blob = client.bucket(bucket_name).blob(blob_name)
    return blob.generate_signed_url(version="v4", expiration=expiration, method="GET")


def generate_signed_urls_for_files(
    client: SigningClient,
    bucket_name: str,
    filenames: list[str],
    expiration: timedelta = DEFAULT_EXPIRATION,
) -> dict[str, str]:
    """Generate signed URLs for a batch of filenames.

    Filenames that fail to sign (e.g. missing from the bucket) are
    silently skipped rather than aborting the whole batch -- a single
    bad object shouldn't block the rest of the report from rendering.
    """
    urls: dict[str, str] = {}
    for filename in filenames:
        try:
            urls[filename] = generate_signed_url(client, bucket_name, filename, expiration)
        except Exception:
            continue
    return urls
