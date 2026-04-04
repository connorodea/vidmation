"""Shared test fixtures for VIDMATION."""

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from vidmation.models.base import Base


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory(prefix="vidmation_test_") as d:
        yield Path(d)


@pytest.fixture
def db_session(tmp_dir):
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_script():
    """Return a sample script JSON for testing."""
    return {
        "title": "5 Signs of Spiritual Awakening",
        "description": "Discover the subtle signs that indicate you are awakening.",
        "tags": ["spirituality", "awakening", "meditation"],
        "hook": "Have you ever felt like something inside you is shifting?",
        "sections": [
            {
                "section_number": 1,
                "heading": "Heightened Intuition",
                "narration": "The first sign is a noticeable increase in your intuitive abilities.",
                "visual_query": "person meditating peaceful nature sunlight",
                "visual_type": "video",
                "estimated_duration_seconds": 45,
            },
            {
                "section_number": 2,
                "heading": "Emotional Sensitivity",
                "narration": "You may find yourself feeling emotions more deeply than before.",
                "visual_query": "sunset ocean waves peaceful",
                "visual_type": "video",
                "estimated_duration_seconds": 40,
            },
        ],
        "outro": "If you resonated with any of these signs, you are on the right path.",
        "total_estimated_duration_seconds": 85,
    }


@pytest.fixture
def sample_word_timestamps():
    """Return sample word-level timestamps from Whisper."""
    return [
        {"word": "The", "start": 0.0, "end": 0.15},
        {"word": "first", "start": 0.15, "end": 0.4},
        {"word": "sign", "start": 0.4, "end": 0.7},
        {"word": "is", "start": 0.7, "end": 0.85},
        {"word": "a", "start": 0.85, "end": 0.95},
        {"word": "noticeable", "start": 0.95, "end": 1.5},
        {"word": "increase", "start": 1.5, "end": 1.9},
        {"word": "in", "start": 1.9, "end": 2.0},
        {"word": "your", "start": 2.0, "end": 2.2},
        {"word": "intuitive", "start": 2.2, "end": 2.7},
        {"word": "abilities", "start": 2.7, "end": 3.3},
    ]
