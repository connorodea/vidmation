"""CSV parser for batch video import — validates and normalizes batch input."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Supported column names (case-insensitive, stripped).
_REQUIRED_COLUMNS = {"topic"}
_OPTIONAL_COLUMNS = {"title", "format", "tags", "schedule_date", "priority", "notes"}
_ALL_COLUMNS = _REQUIRED_COLUMNS | _OPTIONAL_COLUMNS

_VALID_FORMATS = {"landscape", "portrait", "short"}
_VALID_PRIORITIES = {"low", "normal", "high", "urgent"}


@dataclass
class BatchRow:
    """A single validated row from a batch CSV file."""

    topic: str
    title: str = ""
    format: str = "landscape"
    tags: list[str] = field(default_factory=list)
    schedule_date: datetime | None = None
    priority: str = "normal"
    notes: str = ""
    row_number: int = 0  # 1-indexed original row number


@dataclass
class ParseResult:
    """Result of parsing a CSV file, including any warnings."""

    rows: list[BatchRow]
    warnings: list[str]
    skipped_count: int


class BatchCSVParser:
    """Parse and validate CSV files for batch video generation.

    Supported columns (all case-insensitive):
    - **topic** (required): The video topic / prompt.
    - **title** (optional): Pre-defined video title override.
    - **format** (optional): Video format — ``landscape``, ``portrait``, ``short``.
    - **tags** (optional): Comma-separated or semicolon-separated tags.
    - **schedule_date** (optional): ISO date or ``YYYY-MM-DD`` for scheduling.
    - **priority** (optional): ``low``, ``normal``, ``high``, ``urgent``.
    - **notes** (optional): Free-text notes for the producer.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("aividio.batch.CSVParser")

    def parse(self, csv_path: Path) -> list[BatchRow]:
        """Parse a CSV file and return validated rows.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            List of :class:`BatchRow` objects.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
            ValueError: If the CSV is malformed or missing required columns.
        """
        result = self.parse_detailed(csv_path)

        for warning in result.warnings:
            self.logger.warning(warning)

        if result.skipped_count > 0:
            self.logger.warning(
                "Skipped %d invalid rows in %s", result.skipped_count, csv_path
            )

        return result.rows

    def parse_detailed(self, csv_path: Path) -> ParseResult:
        """Parse a CSV file with detailed results including warnings.

        Args:
            csv_path: Path to the CSV file.

        Returns:
            A :class:`ParseResult` with rows, warnings, and skip count.
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        rows: list[BatchRow] = []
        warnings: list[str] = []
        skipped = 0

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            # Sniff the dialect for flexibility (handles comma, semicolon, tab).
            sample = f.read(4096)
            f.seek(0)

            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel  # type: ignore[assignment]

            reader = csv.DictReader(f, dialect=dialect)

            if reader.fieldnames is None:
                raise ValueError(f"CSV file appears empty: {csv_path}")

            # Normalize header names.
            normalized_headers = {
                h.strip().lower(): h for h in reader.fieldnames
            }

            # Validate required columns.
            if "topic" not in normalized_headers:
                raise ValueError(
                    f"CSV file must contain a 'topic' column. "
                    f"Found columns: {list(reader.fieldnames)}"
                )

            # Warn about unknown columns.
            unknown = set(normalized_headers.keys()) - _ALL_COLUMNS
            if unknown:
                warnings.append(
                    f"Unknown columns will be ignored: {sorted(unknown)}"
                )

            for row_num, raw_row in enumerate(reader, start=2):
                try:
                    parsed = self._parse_row(raw_row, normalized_headers, row_num)
                    if parsed is not None:
                        rows.append(parsed)
                    else:
                        skipped += 1
                except Exception as exc:
                    warnings.append(f"Row {row_num}: {exc}")
                    skipped += 1

        self.logger.info(
            "Parsed %s: %d valid rows, %d skipped",
            csv_path.name,
            len(rows),
            skipped,
        )
        return ParseResult(rows=rows, warnings=warnings, skipped_count=skipped)

    def _parse_row(
        self,
        raw_row: dict[str, str],
        headers: dict[str, str],
        row_number: int,
    ) -> BatchRow | None:
        """Parse and validate a single CSV row."""

        def _get(col: str) -> str:
            """Get the value of a column by normalized name."""
            original_name = headers.get(col, "")
            return (raw_row.get(original_name) or "").strip()

        # Topic is required.
        topic = _get("topic")
        if not topic:
            self.logger.debug("Skipping row %d: empty topic", row_number)
            return None

        # Format validation.
        fmt = _get("format").lower() or "landscape"
        if fmt not in _VALID_FORMATS:
            self.logger.warning(
                "Row %d: invalid format '%s', defaulting to 'landscape'",
                row_number,
                fmt,
            )
            fmt = "landscape"

        # Tags parsing — support comma and semicolon separators.
        tags_raw = _get("tags")
        tags: list[str] = []
        if tags_raw:
            # Try semicolons first, then commas.
            if ";" in tags_raw:
                tags = [t.strip() for t in tags_raw.split(";") if t.strip()]
            else:
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        # Schedule date parsing.
        schedule_date: datetime | None = None
        schedule_raw = _get("schedule_date")
        if schedule_raw:
            schedule_date = self._parse_date(schedule_raw, row_number)

        # Priority validation.
        priority = _get("priority").lower() or "normal"
        if priority not in _VALID_PRIORITIES:
            self.logger.warning(
                "Row %d: invalid priority '%s', defaulting to 'normal'",
                row_number,
                priority,
            )
            priority = "normal"

        return BatchRow(
            topic=topic,
            title=_get("title"),
            format=fmt,
            tags=tags,
            schedule_date=schedule_date,
            priority=priority,
            notes=_get("notes"),
            row_number=row_number,
        )

    def _parse_date(self, value: str, row_number: int) -> datetime | None:
        """Try to parse a date string in common formats."""
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        self.logger.warning(
            "Row %d: could not parse schedule_date '%s', ignoring",
            row_number,
            value,
        )
        return None
