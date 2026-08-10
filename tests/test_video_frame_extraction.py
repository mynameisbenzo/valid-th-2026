import json

import pytest
from PIL import Image

from valid_video.video_frame_extraction import extract_frame, probe_duration


class FakeResult:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def make_probe_runner(duration_seconds=10.0, returncode=0):
    def runner(cmd, capture_output, text, timeout):
        stdout = json.dumps({"format": {"duration": str(duration_seconds)}})
        return FakeResult(returncode=returncode, stdout=stdout)

    return runner


class TestProbeDuration:
    def test_returns_duration_in_seconds(self):
        runner = make_probe_runner(duration_seconds=12.5)
        assert probe_duration("video.mp4", runner=runner) == 12.5

    def test_command_uses_ffprobe(self):
        captured = {}

        def runner(cmd, capture_output, text, timeout):
            captured["cmd"] = cmd
            return FakeResult(stdout=json.dumps({"format": {"duration": "5.0"}}))

        probe_duration("video.mp4", runner=runner)
        assert captured["cmd"][0] == "ffprobe"
        assert "video.mp4" in captured["cmd"]

    def test_nonzero_returncode_raises(self):
        runner = make_probe_runner(returncode=1)
        with pytest.raises(RuntimeError):
            probe_duration("missing.mp4", runner=runner)


def make_extract_runner(image_to_write=None):
    """Fake ffmpeg runner that writes a real small image to the output path,
    so downstream PIL.Image.open() calls in tests succeed."""

    def runner(cmd, capture_output, text, timeout):
        output_path = cmd[-1]
        img = image_to_write or Image.new("RGB", (4, 4), "purple")
        img.save(output_path)
        return FakeResult(returncode=0)

    return runner


class TestExtractFrame:
    def test_writes_an_image_file(self, tmp_path):
        output_path = tmp_path / "frame.jpg"
        extract_frame(
            "video.mp4",
            str(output_path),
            probe_runner=make_probe_runner(duration_seconds=10.0),
            extract_runner=make_extract_runner(),
        )
        assert output_path.exists()
        # confirm it's a valid, openable image
        Image.open(output_path).verify()

    def test_seeks_to_midpoint_by_default(self, tmp_path):
        captured = {}

        def extract_runner(cmd, capture_output, text, timeout):
            captured["cmd"] = cmd
            Image.new("RGB", (4, 4)).save(cmd[-1])
            return FakeResult(returncode=0)

        extract_frame(
            "video.mp4",
            str(tmp_path / "frame.jpg"),
            probe_runner=make_probe_runner(duration_seconds=10.0),
            extract_runner=extract_runner,
        )
        ss_index = captured["cmd"].index("-ss")
        assert captured["cmd"][ss_index + 1] == "5.0"

    def test_custom_timestamp_fraction(self, tmp_path):
        captured = {}

        def extract_runner(cmd, capture_output, text, timeout):
            captured["cmd"] = cmd
            Image.new("RGB", (4, 4)).save(cmd[-1])
            return FakeResult(returncode=0)

        extract_frame(
            "video.mp4",
            str(tmp_path / "frame.jpg"),
            timestamp_fraction=0.25,
            probe_runner=make_probe_runner(duration_seconds=8.0),
            extract_runner=extract_runner,
        )
        ss_index = captured["cmd"].index("-ss")
        assert captured["cmd"][ss_index + 1] == "2.0"

    def test_extraction_failure_raises_runtime_error(self, tmp_path):
        def failing_runner(cmd, capture_output, text, timeout):
            return FakeResult(returncode=1, stderr="ffmpeg exploded")

        with pytest.raises(RuntimeError, match="ffmpeg exploded"):
            extract_frame(
                "video.mp4",
                str(tmp_path / "frame.jpg"),
                probe_runner=make_probe_runner(),
                extract_runner=failing_runner,
            )
