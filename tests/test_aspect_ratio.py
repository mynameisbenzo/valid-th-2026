import pytest

from valid_video.aspect_ratio import classify_aspect_ratio, simplify_ratio


class TestExactRatios:
    def test_9x16_exact(self):
        assert classify_aspect_ratio(1080, 1920) == "9:16"

    def test_1x1_exact(self):
        assert classify_aspect_ratio(1080, 1080) == "1:1"

    def test_4x5_exact(self):
        assert classify_aspect_ratio(1080, 1350) == "4:5"

    def test_16x9_exact(self):
        assert classify_aspect_ratio(1920, 1080) == "16:9"


class TestToleranceWithinOnePercent:
    def test_slightly_off_9x16_still_matches(self):
        # 1080x1920 is exactly 0.5625. Nudge height down ~0.9%.
        assert classify_aspect_ratio(1080, 1903) == "9:16"

    def test_slightly_off_16x9_still_matches(self):
        # 1920x1085 is ~0.44% off true 16:9 -- within tolerance
        assert classify_aspect_ratio(1920, 1085) == "16:9"

    def test_common_alternate_resolution_matches_1x1(self):
        # square videos aren't always 1080x1080
        assert classify_aspect_ratio(720, 722) == "1:1"


class TestOutsideTolerance_ReturnsOther:
    def test_ratio_between_buckets_is_other(self):
        # 3:4 (0.75) sits between 4:5 (0.8) and nothing else close by
        assert classify_aspect_ratio(1080, 1440) == "other"

    def test_far_off_ratio_is_other(self):
        assert classify_aspect_ratio(2000, 500) == "other"


class TestInvalidInput:
    def test_zero_height_raises(self):
        with pytest.raises(ValueError):
            classify_aspect_ratio(1080, 0)

    def test_negative_dimension_raises(self):
        with pytest.raises(ValueError):
            classify_aspect_ratio(-100, 100)


class TestSimplifyRatio:
    def test_exact_canonical_ratios_reduce_cleanly(self):
        assert simplify_ratio(1080, 1920) == "9:16"
        assert simplify_ratio(1080, 1080) == "1:1"
        assert simplify_ratio(1080, 1350) == "4:5"
        assert simplify_ratio(1920, 1080) == "16:9"

    def test_non_canonical_ratio_reduces_to_its_own_fraction(self):
        # 1470x630 reduces via gcd(1470, 630)=210 -> 7:3
        assert simplify_ratio(1470, 630) == "7:3"

    def test_odd_resolution_still_reduces_correctly(self):
        # gcd(576, 1024) = 64 -> 9:16
        assert simplify_ratio(576, 1024) == "9:16"

    def test_coprime_dimensions_are_unchanged(self):
        assert simplify_ratio(7, 3) == "7:3"

    def test_zero_or_negative_dimension_raises(self):
        with pytest.raises(ValueError):
            simplify_ratio(0, 100)
        with pytest.raises(ValueError):
            simplify_ratio(100, -5)
