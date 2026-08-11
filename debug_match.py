"""Debug helper: print pairwise visual similarity between video files and
save the extracted representative frame from each, so you can see exactly
what the matcher is comparing.

Usage:
    python debug_match.py video_a.mp4 video_b.mp4 [video_c.mp4 ...]
"""

import itertools
import os
import sys

from valid_video.video_frame_extraction import extract_frame
from valid_video.visual_matching import compare_videos_visual
from valid_video.visual_similarity import normalize_frame
from PIL import Image

if len(sys.argv) < 3:
    print("Usage: python debug_match.py video1.mp4 video2.mp4 [video3.mp4 ...]")
    sys.exit(1)

videos = sys.argv[1:]
debug_dir = "debug_frames"
os.makedirs(debug_dir, exist_ok=True)

print("Extracting representative frames...")
for v in videos:
    out_path = os.path.join(debug_dir, os.path.basename(v) + "_frame.jpg")
    try:
        extract_frame(v, out_path)
        with Image.open(out_path) as img:
            normalized = normalize_frame(img)
            normalized.save(os.path.join(debug_dir, os.path.basename(v) + "_normalized.jpg"))
        print(f"  OK: {v} -> {out_path} (and _normalized.jpg)")
    except Exception as e:
        print(f"  FAILED extracting {v}: {e}")

print("\nPairwise similarity (threshold for a match is 0.80):")
for a, b in itertools.combinations(videos, 2):
    try:
        score = compare_videos_visual(a, b)
        flag = "MATCH" if score >= 0.80 else "no match"
        print(f"  {os.path.basename(a)}  <->  {os.path.basename(b)}:  {score:.3f}  [{flag}]")
    except Exception as e:
        print(f"  FAILED comparing {a} vs {b}: {e}")

print(f"\nCheck the '{debug_dir}/' folder -- look at the *_normalized.jpg files especially,")
print("since that's literally what the matcher hashes and compares.")
