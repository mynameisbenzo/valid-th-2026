import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from valid_video.api import create_app

# Exact filenames/dimensions from the real product spec, so these tests
# double as a spec-conformance check.
UGC_9_16 = "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@CadenceLovesAliens17_InteractingWithAPink_4685__AS_9-16.mp4"
UGC_1_1 = "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@CadenceLovesAliens17_InteractingWithAPink_4685__AS_1-1.mp4"
UGC_4_5 = "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@CadenceLovesAliens17_InteractingWithAPink_4685__AS_4-5.mp4"
AI_AD_16_9 = "AI_Ad_Agency_Video_Creation.mp4"
CINEMATIC_OTHER = "Cinematic_Ultrawide_Brand_Ad.mp4"

DIMENSIONS_BY_FILENAME = {
    UGC_9_16: (576, 1024),
    UGC_1_1: (576, 576),
    UGC_4_5: (1080, 1350),
    AI_AD_16_9: (1280, 720),
    CINEMATIC_OTHER: (1470, 630),
}

# Which "visual content group" each file belongs to, for the fake ffmpeg
# frame extractor -- same group -> identical fake frame -> similarity 1.0.
CONTENT_GROUP_BY_FILENAME = {
    UGC_9_16: "ugc",
    UGC_1_1: "ugc",
    UGC_4_5: "ugc",
    AI_AD_16_9: "ai_ad",
    CINEMATIC_OTHER: "cinematic",
}

def _shaped_frame(pattern):
    img = Image.new("RGB", (64, 64), (90, 90, 90))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    if pattern == "circle":
        img = Image.new("RGB", (64, 64), (90, 90, 90))
        draw = ImageDraw.Draw(img)
        draw.ellipse([16, 16, 48, 48], fill=(255, 140, 0))
    elif pattern == "corner_square":
        img = Image.new("RGB", (64, 64), (10, 10, 10))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 20, 20], fill=(200, 200, 255))
    elif pattern == "stripes":
        img = Image.new("RGB", (64, 64), (20, 90, 20))
        draw = ImageDraw.Draw(img)
        for i in range(-64, 64, 8):
            draw.line([(i, 0), (i + 64, 64)], fill=(255, 255, 0), width=4)
    return img


FRAME_BY_GROUP = {
    "ugc": _shaped_frame("circle"),
    "ai_ad": _shaped_frame("corner_square"),
    "cinematic": _shaped_frame("stripes"),
}


def _filename_for_source(source: str) -> str:
    for fname in DIMENSIONS_BY_FILENAME:
        if fname in source:
            return fname
    raise ValueError(f"no fixture filename found in source path: {source}")


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def fake_probe_runner(cmd, capture_output, text, timeout):
    source = cmd[-1]
    fname = _filename_for_source(source)
    if "stream=width,height" in cmd:
        width, height = DIMENSIONS_BY_FILENAME[fname]
        return FakeResult(stdout=json.dumps({"streams": [{"width": width, "height": height}]}))
    else:  # duration probe
        return FakeResult(stdout=json.dumps({"format": {"duration": "2.0"}}))


def fake_extract_runner(cmd, capture_output, text, timeout):
    source = cmd[cmd.index("-i") + 1]
    output_path = cmd[-1]
    fname = _filename_for_source(source)
    group = CONTENT_GROUP_BY_FILENAME[fname]
    FRAME_BY_GROUP[group].save(output_path)
    return FakeResult(returncode=0)


def sequential_id_generator(start=10000000):
    n = start
    while True:
        yield str(n)
        n += 1


@pytest.fixture
def client(tmp_path):
    id_gen = sequential_id_generator()
    app = create_app(
        probe_runner=fake_probe_runner,
        extract_runner=fake_extract_runner,
        id_generator=lambda: next(id_gen),
        upload_dir=str(tmp_path),
    )
    return TestClient(app)


def upload_all(client):
    files = [
        ("files", (fname, io.BytesIO(b"fake mp4 bytes"), "video/mp4"))
        for fname in DIMENSIONS_BY_FILENAME
    ]
    response = client.post("/upload", files=files)
    assert response.status_code == 200
    return response.json()


class TestIndexPage:
    def test_serves_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "dropzone" in response.text


class TestUpload:
    def test_returns_expected_fields_for_each_file(self, client):
        results = upload_all(client)
        assert len(results) == 5

        by_filename = {r["filename"]: r for r in results}
        ugc_9_16 = by_filename[UGC_9_16]
        assert ugc_9_16["width"] == 576
        assert ugc_9_16["height"] == 1024
        assert ugc_9_16["aspect_ratio"] == "9:16"
        assert ugc_9_16["ratio_bucket"] == "9:16"
        assert "video_id" in ugc_9_16

        cinematic = by_filename[CINEMATIC_OTHER]
        assert cinematic["aspect_ratio"] == "7:3"
        assert cinematic["ratio_bucket"] == "Other"


class TestMatch:
    def test_returns_cross_bucket_siblings_sorted_by_confidence(self, client):
        results = upload_all(client)
        by_filename = {r["filename"]: r for r in results}
        query_id = by_filename[UGC_9_16]["video_id"]

        response = client.get("/match", params={"video_id": query_id})
        assert response.status_code == 200
        matches = response.json()

        matched_filenames = {m["filename"] for m in matches}
        assert matched_filenames == {UGC_1_1, UGC_4_5}
        assert query_id not in {m["video_id"] for m in matches}
        for m in matches:
            assert 0.0 <= m["confidence"] <= 1.0
        # sorted descending
        confidences = [m["confidence"] for m in matches]
        assert confidences == sorted(confidences, reverse=True)

    def test_unknown_video_id_is_404(self, client):
        response = client.get("/match", params={"video_id": "doesnotexist"})
        assert response.status_code == 404

    def test_excluded_other_video_returns_empty_array_not_404(self, client):
        results = upload_all(client)
        by_filename = {r["filename"]: r for r in results}
        other_id = by_filename[CINEMATIC_OTHER]["video_id"]

        response = client.get("/match", params={"video_id": other_id})
        assert response.status_code == 200
        assert response.json() == []

    def test_video_with_no_siblings_returns_empty_array(self, client):
        results = upload_all(client)
        by_filename = {r["filename"]: r for r in results}
        lone_id = by_filename[AI_AD_16_9]["video_id"]

        response = client.get("/match", params={"video_id": lone_id})
        assert response.status_code == 200
        assert response.json() == []


class TestListVideos:
    def test_lists_all_uploaded(self, client):
        upload_all(client)
        response = client.get("/videos")
        assert response.status_code == 200
        assert len(response.json()) == 5

    def test_filters_by_ratio_query_param(self, client):
        upload_all(client)
        response = client.get("/videos", params={"ratio": "9:16"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 1
        assert results[0]["filename"] == UGC_9_16


class TestDeleteVideo:
    def test_deletes_and_returns_deleted_id(self, client):
        results = upload_all(client)
        video_id = results[0]["video_id"]

        response = client.delete(f"/videos/{video_id}")
        assert response.status_code == 200
        assert response.json() == {"deleted": video_id}

        # no longer listed
        remaining = client.get("/videos").json()
        assert video_id not in {r["video_id"] for r in remaining}

    def test_unknown_id_is_404(self, client):
        response = client.delete("/videos/doesnotexist")
        assert response.status_code == 404
