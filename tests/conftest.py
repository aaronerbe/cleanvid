"""
Pytest configuration and shared fixtures for cleanvid tests.
"""

import pytest
from pathlib import Path
from datetime import datetime
from cleanvid.models.subtitle import SubtitleEntry, SubtitleFile
from cleanvid.models.segment import MuteSegment
from cleanvid.models.config import Settings


@pytest.fixture
def temp_video_file(tmp_path):
    """Create a temporary video file."""
    video_file = tmp_path / "test_video.mkv"
    video_file.write_bytes(b"fake video content")
    return video_file


@pytest.fixture
def temp_subtitle_file(tmp_path):
    """Create a temporary subtitle file with sample content."""
    subtitle_file = tmp_path / "test.srt"
    content = """1
00:00:10,500 --> 00:00:15,200
This is the first subtitle

2
00:00:20,000 --> 00:00:25,500
This one contains damn profanity

3
00:00:30,100 --> 00:00:35,800
Final subtitle here
"""
    subtitle_file.write_text(content, encoding="utf-8")
    return subtitle_file


@pytest.fixture
def sample_subtitle_entries():
    """Create sample subtitle entries for testing."""
    return [
        SubtitleEntry(
            index=1,
            start_time=10.5,
            end_time=15.2,
            text="This is the first subtitle"
        ),
        SubtitleEntry(
            index=2,
            start_time=20.0,
            end_time=25.5,
            text="This one contains damn profanity"
        ),
        SubtitleEntry(
            index=3,
            start_time=30.1,
            end_time=35.8,
            text="Final subtitle here"
        ),
    ]


@pytest.fixture
def sample_mute_segments():
    """Create sample mute segments for testing."""
    return [
        MuteSegment(
            start_time=10.0,
            end_time=11.0,
            word="damn",
            confidence=0.95
        ),
        MuteSegment(
            start_time=20.0,
            end_time=21.0,
            word="hell",
            confidence=0.90
        ),
        MuteSegment(
            start_time=30.0,
            end_time=31.5,
            word="shit",
            confidence=0.98
        ),
    ]


@pytest.fixture
def sample_word_list(tmp_path):
    """Create a sample profanity word list file."""
    word_list_file = tmp_path / "profanity_words.txt"
    words = """# Sample profanity list
damn
hell
shit
f*ck
ass
# End of list
"""
    word_list_file.write_text(words, encoding="utf-8")
    return word_list_file


@pytest.fixture
def default_settings():
    """Create default settings for testing."""
    return Settings()


@pytest.fixture
def test_config_dir(tmp_path):
    """Create a temporary config directory structure."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    return {
        "root": tmp_path,
        "config": config_dir,
        "logs": logs_dir,
        "input": input_dir,
        "output": output_dir,
    }


# Marks for organizing tests
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
