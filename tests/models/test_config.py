"""
Unit tests for configuration models.

Tests all configuration classes and validation logic.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

from cleanvid.models.config import (
    ProcessingConfig,
    PathConfig,
    OpenSubtitlesConfig,
    FFmpegConfig,
    Settings,
    Credentials,
)


class TestProcessingConfig:
    """Test ProcessingConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = ProcessingConfig()
        assert config.max_daily_processing == 5
        assert config.video_extensions == [".mkv", ".mp4", ".avi", ".mov", ".m4v"]
        assert config.mute_padding_before_ms == 500
        assert config.mute_padding_after_ms == 500
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = ProcessingConfig(
            max_daily_processing=10,
            video_extensions=[".mkv", ".mp4"],
            mute_padding_before_ms=1000,
            mute_padding_after_ms=750
        )
        assert config.max_daily_processing == 10
        assert config.video_extensions == [".mkv", ".mp4"]
        assert config.mute_padding_before_ms == 1000
        assert config.mute_padding_after_ms == 750
    
    def test_validates_max_daily_processing_positive(self):
        """Test max_daily_processing must be positive."""
        with pytest.raises(ValidationError):
            ProcessingConfig(max_daily_processing=0)
        
        with pytest.raises(ValidationError):
            ProcessingConfig(max_daily_processing=-1)
    
    def test_validates_padding_non_negative(self):
        """Test padding values must be non-negative."""
        with pytest.raises(ValidationError):
            ProcessingConfig(mute_padding_before_ms=-100)
        
        with pytest.raises(ValidationError):
            ProcessingConfig(mute_padding_after_ms=-50)
    
    def test_normalizes_extensions_with_dots(self):
        """Test extensions are normalized to start with dot."""
        config = ProcessingConfig(video_extensions=["mkv", ".mp4", "avi"])
        assert config.video_extensions == [".mkv", ".mp4", ".avi"]


class TestPathConfig:
    """Test PathConfig model."""
    
    def test_default_paths(self):
        """Test default path values."""
        config = PathConfig()
        assert config.input_dir == Path("/input")
        assert config.output_dir == Path("/output")
        assert config.config_dir == Path("/config")
        assert config.logs_dir == Path("/logs")
    
    def test_custom_paths(self):
        """Test custom path values."""
        config = PathConfig(
            input_dir=Path("/data/movies"),
            output_dir=Path("/data/filtered"),
            config_dir=Path("/etc/cleanvid"),
            logs_dir=Path("/var/log/cleanvid")
        )
        assert config.input_dir == Path("/data/movies")
        assert config.output_dir == Path("/data/filtered")
        assert config.config_dir == Path("/etc/cleanvid")
        assert config.logs_dir == Path("/var/log/cleanvid")
    
    def test_validates_absolute_paths(self):
        """Test that paths must be absolute."""
        with pytest.raises(ValidationError):
            PathConfig(input_dir=Path("relative/path"))
        
        with pytest.raises(ValidationError):
            PathConfig(output_dir=Path("another/relative"))


class TestOpenSubtitlesConfig:
    """Test OpenSubtitlesConfig model."""
    
    def test_default_values(self):
        """Test default OpenSubtitles configuration."""
        config = OpenSubtitlesConfig()
        assert config.enabled is True
        assert config.language == "en"
        assert config.username is None
        assert config.password is None
        assert config.api_key is None
    
    def test_with_credentials(self):
        """Test OpenSubtitles config with credentials."""
        config = OpenSubtitlesConfig(
            username="testuser",
            password="testpass",
            api_key="test-api-key"
        )
        assert config.username == "testuser"
        assert config.password == "testpass"
        assert config.api_key == "test-api-key"
    
    def test_disabled_mode(self):
        """Test disabling OpenSubtitles."""
        config = OpenSubtitlesConfig(enabled=False)
        assert config.enabled is False


class TestFFmpegConfig:
    """Test FFmpegConfig model."""
    
    def test_default_values(self):
        """Test default FFmpeg configuration."""
        config = FFmpegConfig()
        assert config.threads == 2
        assert config.audio_codec == "aac"
        assert config.audio_bitrate == "192k"
        assert config.re_encode_video is False
        assert config.video_codec is None
        assert config.video_crf == 23
    
    def test_custom_values(self):
        """Test custom FFmpeg configuration."""
        config = FFmpegConfig(
            threads=4,
            audio_codec="mp3",
            audio_bitrate="256k",
            re_encode_video=True,
            video_codec="libx264",
            video_crf=20
        )
        assert config.threads == 4
        assert config.audio_codec == "mp3"
        assert config.audio_bitrate == "256k"
        assert config.re_encode_video is True
        assert config.video_codec == "libx264"
        assert config.video_crf == 20
    
    def test_validates_threads_range(self):
        """Test thread count must be in valid range."""
        with pytest.raises(ValidationError):
            FFmpegConfig(threads=0)
        
        with pytest.raises(ValidationError):
            FFmpegConfig(threads=17)
        
        # Valid boundary values
        config1 = FFmpegConfig(threads=1)
        assert config1.threads == 1
        
        config16 = FFmpegConfig(threads=16)
        assert config16.threads == 16
    
    def test_validates_crf_range(self):
        """Test CRF must be in valid range."""
        with pytest.raises(ValidationError):
            FFmpegConfig(video_crf=-1)
        
        with pytest.raises(ValidationError):
            FFmpegConfig(video_crf=52)
        
        # Valid boundary values
        config0 = FFmpegConfig(video_crf=0)
        assert config0.video_crf == 0
        
        config51 = FFmpegConfig(video_crf=51)
        assert config51.video_crf == 51


class TestSettings:
    """Test main Settings model."""
    
    def test_default_settings(self):
        """Test default settings configuration."""
        settings = Settings()
        
        # Check nested configs exist
        assert isinstance(settings.processing, ProcessingConfig)
        assert isinstance(settings.paths, PathConfig)
        assert isinstance(settings.opensubtitles, OpenSubtitlesConfig)
        assert isinstance(settings.ffmpeg, FFmpegConfig)
    
    def test_custom_settings(self):
        """Test custom settings configuration."""
        settings = Settings(
            processing=ProcessingConfig(max_daily_processing=10),
            paths=PathConfig(input_dir=Path("/custom/input")),
            opensubtitles=OpenSubtitlesConfig(language="es"),
            ffmpeg=FFmpegConfig(threads=4)
        )
        
        assert settings.processing.max_daily_processing == 10
        assert settings.paths.input_dir == Path("/custom/input")
        assert settings.opensubtitles.language == "es"
        assert settings.ffmpeg.threads == 4
    
    def test_get_word_list_path(self):
        """Test word list path helper."""
        settings = Settings()
        word_list_path = settings.get_word_list_path()
        assert word_list_path == Path("/config/profanity_words.txt")
    
    def test_get_processed_log_path(self):
        """Test processed log path helper."""
        settings = Settings()
        log_path = settings.get_processed_log_path()
        assert log_path == Path("/config/processed_log.json")
    
    def test_get_log_file_path(self):
        """Test log file path helper."""
        settings = Settings()
        log_path = settings.get_log_file_path()
        assert log_path == Path("/logs/cleanvid.log")
    
    def test_rejects_unknown_fields(self):
        """Test that unknown fields are rejected."""
        with pytest.raises(ValidationError):
            Settings(unknown_field="value")
    
    def test_validates_nested_configs(self):
        """Test that nested config validation works."""
        with pytest.raises(ValidationError):
            Settings(
                processing=ProcessingConfig(max_daily_processing=-1)
            )


class TestCredentials:
    """Test Credentials dataclass."""
    
    def test_basic_credentials(self):
        """Test creating credentials without API key."""
        creds = Credentials(username="user", password="pass")
        assert creds.username == "user"
        assert creds.password == "pass"
        assert creds.api_key is None
    
    def test_credentials_with_api_key(self):
        """Test creating credentials with API key."""
        creds = Credentials(
            username="user",
            password="pass",
            api_key="key123"
        )
        assert creds.username == "user"
        assert creds.password == "pass"
        assert creds.api_key == "key123"


class TestSettingsIntegration:
    """Integration tests for complete settings."""
    
    def test_complete_configuration(self):
        """Test complete configuration with all options."""
        settings = Settings(
            processing=ProcessingConfig(
                max_daily_processing=20,
                video_extensions=[".mkv", ".mp4"],
                mute_padding_before_ms=1000,
                mute_padding_after_ms=1000
            ),
            paths=PathConfig(
                input_dir=Path("/volume1/movies/original"),
                output_dir=Path("/volume1/movies/filtered"),
                config_dir=Path("/volume1/docker/cleanvid/config"),
                logs_dir=Path("/volume1/docker/cleanvid/logs")
            ),
            opensubtitles=OpenSubtitlesConfig(
                enabled=True,
                language="en",
                username="testuser",
                password="testpass",
                api_key="test-key"
            ),
            ffmpeg=FFmpegConfig(
                threads=4,
                audio_codec="aac",
                audio_bitrate="256k",
                re_encode_video=False
            )
        )
        
        # Verify all settings
        assert settings.processing.max_daily_processing == 20
        assert settings.paths.input_dir == Path("/volume1/movies/original")
        assert settings.opensubtitles.username == "testuser"
        assert settings.ffmpeg.threads == 4
        
        # Verify helper methods work
        assert settings.get_word_list_path() == Path(
            "/volume1/docker/cleanvid/config/profanity_words.txt"
        )
