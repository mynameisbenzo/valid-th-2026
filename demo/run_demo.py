"""Run the real pipeline end-to-end against local sample videos.

No mocks: real ffprobe subprocess calls, real classification logic,
real filename-stem matching. Only the GCS client is swapped for a
local-filesystem stand-in (see local_fs_client.py) so this runs
without cloud credentials.

Usage:
    python demo/run_demo.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo.local_fs_client import LocalFilesystemClient
from valid_video.pipeline import build_report

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    bucket_name = sys.argv[1] if len(sys.argv) > 1 else "sample_videos"
    client = LocalFilesystemClient(base_directory=DEMO_DIR)
    report = build_report(client, bucket_name=bucket_name)
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
