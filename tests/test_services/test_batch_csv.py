"""Tests for batch CSV parser — validates and normalizes batch input."""

import pytest

from vidmation.batch.csv_parser import BatchCSVParser, BatchRow


@pytest.fixture
def parser():
    return BatchCSVParser()


class TestBatchCSVValidAllColumns:
    def test_valid_csv_with_all_columns(self, parser, tmp_dir):
        csv_path = tmp_dir / "full.csv"
        csv_path.write_text(
            "topic,title,format,tags,schedule_date,priority,notes\n"
            "AI in 2025,The Future of AI,landscape,\"ai,future\",2025-06-01,high,First video\n"
            "Quantum Computing,Quantum 101,portrait,\"science;quantum\",2025-07-15,normal,Beginner level\n",
            encoding="utf-8",
        )
        rows = parser.parse(csv_path)
        assert len(rows) == 2

        assert rows[0].topic == "AI in 2025"
        assert rows[0].title == "The Future of AI"
        assert rows[0].format == "landscape"
        assert rows[0].priority == "high"
        assert rows[0].notes == "First video"

        assert rows[1].topic == "Quantum Computing"
        assert rows[1].format == "portrait"


class TestBatchCSVTopicOnly:
    def test_csv_with_only_topic_column(self, parser, tmp_dir):
        csv_path = tmp_dir / "topic_only.csv"
        csv_path.write_text(
            "topic\n"
            "How to learn Python\n"
            "Best productivity tips\n"
            "History of the Internet\n",
            encoding="utf-8",
        )
        rows = parser.parse(csv_path)
        assert len(rows) == 3
        assert rows[0].topic == "How to learn Python"
        assert rows[0].format == "landscape"  # default
        assert rows[0].priority == "normal"  # default

    def test_csv_topic_only_defaults(self, parser, tmp_dir):
        csv_path = tmp_dir / "defaults.csv"
        csv_path.write_text("topic\nSingle topic video\n", encoding="utf-8")
        rows = parser.parse(csv_path)
        assert len(rows) == 1
        row = rows[0]
        assert row.title == ""
        assert row.tags == []
        assert row.schedule_date is None
        assert row.notes == ""


class TestBatchCSVMissingTopic:
    def test_csv_missing_topic_column_raises(self, parser, tmp_dir):
        csv_path = tmp_dir / "no_topic.csv"
        csv_path.write_text(
            "title,format\n"
            "Some Title,landscape\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="topic"):
            parser.parse(csv_path)

    def test_csv_with_empty_topic_row_skips(self, parser, tmp_dir):
        csv_path = tmp_dir / "empty_topic.csv"
        csv_path.write_text(
            "topic,title\n"
            "Valid topic,Good\n"
            ",Empty topic\n"
            "Another valid,Also good\n",
            encoding="utf-8",
        )
        rows = parser.parse(csv_path)
        assert len(rows) == 2
        assert rows[0].topic == "Valid topic"
        assert rows[1].topic == "Another valid"


class TestBatchCSVEmpty:
    def test_empty_csv_raises(self, parser, tmp_dir):
        csv_path = tmp_dir / "empty.csv"
        csv_path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            parser.parse(csv_path)

    def test_csv_header_only_returns_empty(self, parser, tmp_dir):
        csv_path = tmp_dir / "header_only.csv"
        csv_path.write_text("topic,title,format\n", encoding="utf-8")
        rows = parser.parse(csv_path)
        assert rows == []


class TestBatchCSVExtraColumns:
    def test_csv_with_extra_unknown_columns(self, parser, tmp_dir):
        csv_path = tmp_dir / "extra_cols.csv"
        csv_path.write_text(
            "topic,title,custom_field,another_unknown\n"
            "My Topic,My Title,custom_value,unknown_value\n",
            encoding="utf-8",
        )
        result = parser.parse_detailed(csv_path)
        assert len(result.rows) == 1
        assert result.rows[0].topic == "My Topic"
        # Warnings should mention unknown columns
        assert len(result.warnings) >= 1
        assert any("unknown" in w.lower() or "Unknown" in w for w in result.warnings)

    def test_csv_extra_columns_do_not_affect_parsing(self, parser, tmp_dir):
        csv_path = tmp_dir / "extra.csv"
        csv_path.write_text(
            "topic,format,extra1,extra2\n"
            "Topic A,portrait,val1,val2\n"
            "Topic B,short,val3,val4\n",
            encoding="utf-8",
        )
        rows = parser.parse(csv_path)
        assert len(rows) == 2
        assert rows[0].format == "portrait"
        assert rows[1].format == "short"


class TestBatchCSVFileNotFound:
    def test_parse_nonexistent_file_raises(self, parser):
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/batch.csv")


class TestBatchCSVTags:
    def test_csv_comma_separated_tags(self, parser, tmp_dir):
        csv_path = tmp_dir / "tags.csv"
        csv_path.write_text(
            'topic,tags\n'
            'My topic,"tag1,tag2,tag3"\n',
            encoding="utf-8",
        )
        rows = parser.parse(csv_path)
        assert rows[0].tags == ["tag1", "tag2", "tag3"]

    def test_csv_semicolon_separated_tags(self, parser, tmp_dir):
        csv_path = tmp_dir / "tags_semi.csv"
        csv_path.write_text(
            'topic,tags\n'
            'My topic,"tag1;tag2;tag3"\n',
            encoding="utf-8",
        )
        rows = parser.parse(csv_path)
        assert rows[0].tags == ["tag1", "tag2", "tag3"]
