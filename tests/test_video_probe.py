import json
import subprocess

import pytest

from valid_video.video_probe import probe_dimensions


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def make_runner(stdout_dict=None, returncode=0, stderr=""):
    """Build a fake `subprocess.run`-shaped callable for injection."""
    stdout = json.dumps(stdout_dict) if stdout_dict is not None else ""

    def runner(cmd, capture_output, text, timeout):
        return FakeCompletedProcess(returncode=returncode, stdout=stdout, stderr=stderr)

    return runner


class TestProbeDimensions:
    def test_returns_width_and_height_from_ffprobe_json(self):
        runner = make_runner({"streams": [{"width": 1080, "height": 1920}]})
        assert probe_dimensions("https://example.com/video.mp4", runner=runner) == (1080, 1920)

    def test_uses_first_video_stream_if_multiple(self):
        runner = make_runner(
            {"streams": [{"width": 1920, "height": 1080}, {"width": 640, "height": 360}]}
        )
        assert probe_dimensions("https://example.com/video.mp4", runner=runner) == (1920, 1080)

    def test_ffprobe_command_includes_source_url(self):
        captured_cmd = {}

        def runner(cmd, capture_output, text, timeout):
            captured_cmd["cmd"] = cmd
            return FakeCompletedProcess(
                returncode=0, stdout=json.dumps({"streams": [{"width": 100, "height": 100}]})
            )

        probe_dimensions("https://example.com/signed?token=abc", runner=runner)
        assert "https://example.com/signed?token=abc" in captured_cmd["cmd"]
        assert captured_cmd["cmd"][0] == "ffprobe"

    def test_nonzero_returncode_raises_runtime_error(self):
        runner = make_runner(returncode=1, stderr="404 not found")
        with pytest.raises(RuntimeError, match="404 not found"):
            probe_dimensions("https://example.com/missing.mp4", runner=runner)

    def test_no_video_streams_raises_value_error(self):
        runner = make_runner({"streams": []})
        with pytest.raises(ValueError, match="no video stream"):
            probe_dimensions("https://example.com/audio_only.mp4", runner=runner)

    def test_malformed_json_raises_value_error(self):
        def runner(cmd, capture_output, text, timeout):
            return FakeCompletedProcess(returncode=0, stdout="not json{{{")

        with pytest.raises(ValueError, match="parse ffprobe output"):
            probe_dimensions("https://example.com/video.mp4", runner=runner)

    def test_timeout_propagates_as_runtime_error(self):
        def runner(cmd, capture_output, text, timeout):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

        with pytest.raises(RuntimeError, match="timed out"):
            probe_dimensions("https://example.com/video.mp4", runner=runner)

    def test_missing_ffprobe_binary_raises_clear_runtime_error(self):
        def runner(cmd, capture_output, text, timeout):
            raise FileNotFoundError(2, "The system cannot find the file specified")

        with pytest.raises(RuntimeError, match="ffprobe"):
            probe_dimensions("video.mp4", runner=runner)
