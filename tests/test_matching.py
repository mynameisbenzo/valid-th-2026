import pytest

from valid_video.matching import extract_stem, group_by_stem


class TestExtractStem:
    def test_strips_extension_and_known_ratio_suffix(self):
        assert extract_stem("campaign123_9-16.mp4") == "campaign123"

    def test_handles_square_ratio(self):
        assert extract_stem("campaign123_1-1.mp4") == "campaign123"

    def test_handles_4x5_ratio(self):
        assert extract_stem("campaign123_4-5.mp4") == "campaign123"

    def test_handles_16x9_ratio(self):
        assert extract_stem("campaign123_16-9.mp4") == "campaign123"

    def test_case_insensitive_extension(self):
        assert extract_stem("campaign123_9-16.MP4") == "campaign123"

    def test_stem_with_underscores_is_preserved(self):
        assert extract_stem("summer_sale_promo_9-16.mp4") == "summer_sale_promo"

    def test_uses_basename_ignores_directory(self):
        assert extract_stem("videos/2024/campaign123_9-16.mp4") == "campaign123"

    def test_no_recognized_ratio_suffix_returns_filename_minus_extension(self):
        # e.g. an "other" bucket video that doesn't follow the ratio-suffix convention
        assert extract_stem("bts_footage_raw.mp4") == "bts_footage_raw"

    def test_unrecognized_ratio_suffix_not_stripped(self):
        # 3-4 isn't one of the four canonical ratios, so we shouldn't strip it --
        # stripping unknown suffixes risks merging unrelated videos.
        assert extract_stem("campaign123_3-4.mp4") == "campaign123_3-4"

    def test_real_world_double_underscore_AS_marker_is_stripped(self):
        # Real agency filenames use `..._{id}__AS_{ratio}.mp4`, not the
        # simpler `..._{ratio}.mp4` convention -- the "__AS" marker
        # should be stripped along with the ratio so the stem is clean.
        name = (
            "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@"
            "CadenceLovesAliens17_InteractingWithAPink_4685__AS_9-16.mp4"
        )
        expected_stem = (
            "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@"
            "CadenceLovesAliens17_InteractingWithAPink_4685"
        )
        assert extract_stem(name) == expected_stem

    def test_filename_with_no_ratio_marker_at_all_is_left_untouched(self):
        assert extract_stem("AI_Ad_Agency_Video_Creation.mp4") == "AI_Ad_Agency_Video_Creation"
        assert extract_stem("Cinematic_Ultrawide_Brand_Ad.mp4") == "Cinematic_Ultrawide_Brand_Ad"


class TestGroupByStem:
    def test_groups_same_stem_across_ratios(self):
        files = [
            "campaign123_9-16.mp4",
            "campaign123_1-1.mp4",
            "campaign123_4-5.mp4",
            "campaign123_16-9.mp4",
        ]
        groups = group_by_stem(files)
        assert groups == {"campaign123": files}

    def test_separates_distinct_campaigns(self):
        files = [
            "campaign123_9-16.mp4",
            "campaign456_9-16.mp4",
            "campaign123_1-1.mp4",
        ]
        groups = group_by_stem(files)
        assert groups == {
            "campaign123": ["campaign123_9-16.mp4", "campaign123_1-1.mp4"],
            "campaign456": ["campaign456_9-16.mp4"],
        }

    def test_singleton_group_for_unmatched_file(self):
        files = ["orphan_clip.mp4"]
        groups = group_by_stem(files)
        assert groups == {"orphan_clip": ["orphan_clip.mp4"]}

    def test_empty_input_returns_empty_dict(self):
        assert group_by_stem([]) == {}

    def test_real_world_upload_example_groups_correctly(self):
        ugc_9x16 = (
            "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@"
            "CadenceLovesAliens17_InteractingWithAPink_4685__AS_9-16.mp4"
        )
        ugc_1x1 = (
            "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@"
            "CadenceLovesAliens17_InteractingWithAPink_4685__AS_1-1.mp4"
        )
        ugc_4x5 = (
            "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@"
            "CadenceLovesAliens17_InteractingWithAPink_4685__AS_4-5.mp4"
        )
        unrelated_a = "AI_Ad_Agency_Video_Creation.mp4"
        unrelated_b = "Cinematic_Ultrawide_Brand_Ad.mp4"

        groups = group_by_stem([ugc_9x16, ugc_1x1, ugc_4x5, unrelated_a, unrelated_b])

        ugc_stem = (
            "PTRL_Video_ProductFeature_UGC_VirtualAssistant_CadenceTt@"
            "CadenceLovesAliens17_InteractingWithAPink_4685"
        )
        assert groups[ugc_stem] == [ugc_9x16, ugc_1x1, ugc_4x5]
        assert groups["AI_Ad_Agency_Video_Creation"] == [unrelated_a]
        assert groups["Cinematic_Ultrawide_Brand_Ad"] == [unrelated_b]
