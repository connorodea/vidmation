"""Tests for caption templates and CaptionAnimator word grouping."""

import pytest

from vidmation.captions.animator import CaptionAnimator
from vidmation.captions.templates import (
    TEMPLATES,
    CaptionTemplate,
    create_custom_template,
    get_template,
    list_templates,
)


class TestListTemplates:
    def test_list_templates_returns_30_plus(self):
        templates = list_templates()
        assert len(templates) >= 30

    def test_list_templates_returns_dicts_with_required_keys(self):
        templates = list_templates()
        required_keys = {"name", "display_name", "description", "animation", "highlight_style"}
        for t in templates:
            assert required_keys.issubset(t.keys()), f"Template {t.get('name')} missing keys"


class TestGetTemplate:
    def test_get_template_hormozi_is_valid(self):
        t = get_template("hormozi")
        assert isinstance(t, CaptionTemplate)
        assert t.name == "hormozi"
        assert t.font_name == "Montserrat-ExtraBold"
        assert t.animation == "pop"

    def test_get_template_hormozi_has_highlight_colors(self):
        t = get_template("hormozi")
        assert len(t.highlight_colors) >= 2
        assert "#FFD700" in t.highlight_colors

    def test_get_template_mrbeast_has_bounce_animation(self):
        t = get_template("mrbeast")
        assert t.animation == "bounce"

    def test_get_template_mrbeast_has_word_bg_highlight(self):
        t = get_template("mrbeast")
        assert t.highlight_style == "word_bg"

    def test_get_template_mrbeast_font_is_impact(self):
        t = get_template("mrbeast")
        assert t.font_name == "Impact"

    def test_get_template_nonexistent_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown caption template"):
            get_template("nonexistent")

    def test_get_template_returns_copy(self):
        t1 = get_template("hormozi")
        t2 = get_template("hormozi")
        assert t1 is not t2
        t1.font_size = 999
        t2_fresh = get_template("hormozi")
        assert t2_fresh.font_size != 999

    def test_get_template_case_insensitive(self):
        t = get_template("Hormozi")
        assert t.name == "hormozi"

    def test_get_template_handles_hyphens_and_spaces(self):
        t = get_template("minimal-white")
        assert t.name == "minimal_white"


class TestCreateCustomTemplate:
    def test_create_custom_template_with_defaults(self):
        custom = create_custom_template("my_custom")
        assert custom.name == "my_custom"
        assert custom.display_name == "My Custom"

    def test_create_custom_template_overrides_field(self):
        custom = create_custom_template(
            "big_text",
            base="hormozi",
            font_size=100,
        )
        assert custom.name == "big_text"
        assert custom.font_size == 100
        # Inherits base values for non-overridden fields
        assert custom.font_name == "Montserrat-ExtraBold"

    def test_create_custom_template_from_different_base(self):
        custom = create_custom_template(
            "custom_minimal",
            base="minimal_white",
            font_size=60,
        )
        assert custom.name == "custom_minimal"
        assert custom.font_name == "Helvetica"  # inherited from minimal_white
        assert custom.font_size == 60

    def test_create_custom_template_is_not_registered(self):
        create_custom_template("unregistered_test")
        assert "unregistered_test" not in TEMPLATES


class TestCaptionAnimatorGroupWords:
    @pytest.fixture
    def animator(self):
        return CaptionAnimator()

    def test_group_words_groups_correctly(self, animator, sample_word_timestamps):
        groups = animator._group_words(sample_word_timestamps, words_per_line=3)
        assert len(groups) > 0
        for group in groups:
            assert "text" in group
            assert "start" in group
            assert "end" in group
            assert "words" in group

    def test_group_words_respects_max_words(self, animator, sample_word_timestamps):
        groups = animator._group_words(sample_word_timestamps, words_per_line=2)
        for group in groups:
            # Each group should have at most words_per_line words,
            # except possibly the last group if a single word was merged
            assert len(group["words"]) <= 3  # 2 + possible merged remainder

    def test_group_words_single_word_per_line(self, animator):
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "World", "start": 0.5, "end": 1.0},
            {"word": "Test", "start": 1.0, "end": 1.5},
        ]
        groups = animator._group_words(words, words_per_line=1)
        # With words_per_line=1, single-word remainders get merged with previous
        assert len(groups) >= 1

    def test_group_words_preserves_timing(self, animator, sample_word_timestamps):
        groups = animator._group_words(sample_word_timestamps, words_per_line=3)
        first_group = groups[0]
        assert first_group["start"] == sample_word_timestamps[0]["start"]
        last_group = groups[-1]
        assert last_group["end"] == sample_word_timestamps[-1]["end"]

    def test_group_words_empty_list(self, animator):
        groups = animator._group_words([], words_per_line=3)
        assert groups == []
