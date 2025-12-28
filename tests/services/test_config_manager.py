"""
Unit tests for ConfigManager service.
"""

import pytest
import json
from pathlib import Path
from cleanvid.services.config_manager import ConfigManager
from cleanvid.models.config import Settings, PathConfig


class TestConfigManager:
    """Test ConfigManager service."""
    
    def test_init_default_path(self):
        """Test initialization with default path."""
        manager = ConfigManager()
        assert manager.config_dir == Path("/config")
        assert manager.config_file == Path("/config/settings.json")
    
    def test_init_custom_path(self, tmp_path):
        """Test initialization with custom path."""
        config_dir = tmp_path / "custom_config"
        manager = ConfigManager(config_dir=config_dir)
        assert manager.config_dir == config_dir
        assert manager.config_file == config_dir / "settings.json"
    
    def test_load_settings_creates_default(self, tmp_path):
        """Test loading creates default config if missing."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        settings = manager.load_settings(create_if_missing=True)
        
        assert isinstance(settings, Settings)
        assert manager.config_file.exists()
    
    def test_load_settings_fails_when_missing(self, tmp_path):
        """Test loading fails if config missing and not creating."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        with pytest.raises(FileNotFoundError):
            manager.load_settings(create_if_missing=False)
    
    def test_load_settings_from_file(self, tmp_path):
        """Test loading settings from existing file."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        config_file = config_dir / "settings.json"
        config_data = {
            "processing": {
                "max_daily_processing": 10,
                "video_extensions": [".mkv"],
                "mute_padding_before_ms": 1000,
                "mute_padding_after_ms": 1000
            },
            "paths": {
                "input_dir": "/custom/input",
                "output_dir": "/custom/output",
                "config_dir": "/custom/config",
                "logs_dir": "/custom/logs"
            },
            "opensubtitles": {
                "enabled": False,
                "language": "es",
                "username": None,
                "password": None,
                "api_key": None
            },
            "ffmpeg": {
                "threads": 4,
                "audio_codec": "aac",
                "audio_bitrate": "256k",
                "re_encode_video": False,
                "video_codec": None,
                "video_crf": 23
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        manager = ConfigManager(config_dir=config_dir)
        settings = manager.load_settings()
        
        assert settings.processing.max_daily_processing == 10
        assert settings.processing.video_extensions == [".mkv"]
        assert settings.opensubtitles.enabled is False
        assert settings.ffmpeg.threads == 4
    
    def test_load_settings_invalid_json(self, tmp_path):
        """Test loading with invalid JSON."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        config_file = config_dir / "settings.json"
        config_file.write_text("{ invalid json }")
        
        manager = ConfigManager(config_dir=config_dir)
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            manager.load_settings()
    
    def test_save_settings(self, tmp_path):
        """Test saving settings."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        settings = Settings()
        settings.processing.max_daily_processing = 20
        
        manager.save_settings(settings)
        
        assert manager.config_file.exists()
        
        # Reload and verify
        loaded_settings = manager.load_settings()
        assert loaded_settings.processing.max_daily_processing == 20
    
    def test_save_settings_creates_directory(self, tmp_path):
        """Test saving creates directory if needed."""
        config_dir = tmp_path / "new" / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        settings = Settings()
        manager.save_settings(settings)
        
        assert config_dir.exists()
        assert manager.config_file.exists()
    
    def test_get_settings_loads_if_needed(self, tmp_path):
        """Test get_settings loads automatically."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        settings = manager.get_settings()
        
        assert isinstance(settings, Settings)
        assert manager._settings is not None
    
    def test_get_settings_returns_cached(self, tmp_path):
        """Test get_settings returns cached instance."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        settings1 = manager.get_settings()
        settings2 = manager.get_settings()
        
        assert settings1 is settings2
    
    def test_reload_settings(self, tmp_path):
        """Test reloading settings from disk."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        # Initial load
        settings1 = manager.get_settings()
        assert settings1.processing.max_daily_processing == 5
        
        # Modify file on disk
        config_data = json.loads(manager.config_file.read_text())
        config_data["processing"]["max_daily_processing"] = 15
        manager.config_file.write_text(json.dumps(config_data))
        
        # Reload
        settings2 = manager.reload_settings()
        
        assert settings2.processing.max_daily_processing == 15
    
    def test_initialize_config_directory(self, tmp_path):
        """Test full config directory initialization."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        manager.initialize_config_directory()
        
        # Check all files created
        assert (config_dir / "settings.json").exists()
        assert (config_dir / "profanity_words.txt").exists()
        assert (config_dir / "processed_log.json").exists()
        assert (config_dir / "README.md").exists()
    
    def test_initialize_preserves_existing_files(self, tmp_path):
        """Test initialization doesn't overwrite existing files."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # Create existing word list
        word_list = config_dir / "profanity_words.txt"
        word_list.write_text("custom\nwords\n")
        
        manager = ConfigManager(config_dir=config_dir)
        manager.initialize_config_directory()
        
        # Should not be overwritten
        content = word_list.read_text()
        assert "custom" in content
        assert "words" in content
    
    def test_validate_config_success(self, test_config_dir):
        """Test successful config validation."""
        config_dir = test_config_dir["config"]
        
        # Create word list
        (config_dir / "profanity_words.txt").write_text("damn\nhell\n")
        
        # Create settings with valid paths
        manager = ConfigManager(config_dir=config_dir)
        settings = Settings(
            paths=PathConfig(
                input_dir=test_config_dir["input"],
                output_dir=test_config_dir["output"],
                config_dir=config_dir,
                logs_dir=test_config_dir["logs"]
            )
        )
        manager.save_settings(settings)
        
        is_valid, errors = manager.validate_config()
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_config_missing_paths(self, tmp_path):
        """Test validation catches missing paths."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        manager = ConfigManager(config_dir=config_dir)
        
        # Create settings with non-existent paths
        settings = Settings(
            paths=PathConfig(
                input_dir=Path("/nonexistent/input"),
                output_dir=Path("/nonexistent/output"),
                config_dir=config_dir,
                logs_dir=Path("/nonexistent/logs")
            )
        )
        manager.save_settings(settings)
        
        # Create word list so it doesn't fail on that
        (config_dir / "profanity_words.txt").write_text("damn\n")
        
        is_valid, errors = manager.validate_config()
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("input_dir" in err for err in errors)
    
    def test_validate_config_missing_word_list(self, test_config_dir):
        """Test validation catches missing word list."""
        config_dir = test_config_dir["config"]
        
        manager = ConfigManager(config_dir=config_dir)
        settings = Settings(
            paths=PathConfig(
                input_dir=test_config_dir["input"],
                output_dir=test_config_dir["output"],
                config_dir=config_dir,
                logs_dir=test_config_dir["logs"]
            )
        )
        manager.save_settings(settings)
        
        is_valid, errors = manager.validate_config()
        
        assert is_valid is False
        assert any("Word list" in err for err in errors)
    
    def test_validate_config_opensubtitles_no_credentials(self, test_config_dir):
        """Test validation warns about OpenSubtitles without credentials."""
        config_dir = test_config_dir["config"]
        (config_dir / "profanity_words.txt").write_text("damn\n")
        
        manager = ConfigManager(config_dir=config_dir)
        settings = Settings(
            paths=PathConfig(
                input_dir=test_config_dir["input"],
                output_dir=test_config_dir["output"],
                config_dir=config_dir,
                logs_dir=test_config_dir["logs"]
            )
        )
        # OpenSubtitles enabled by default, but no credentials
        manager.save_settings(settings)
        
        is_valid, errors = manager.validate_config()
        
        assert is_valid is False
        assert any("OpenSubtitles" in err for err in errors)
    
    def test_get_config_summary(self, tmp_path):
        """Test configuration summary generation."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        settings = Settings()
        manager.save_settings(settings)
        
        summary = manager.get_config_summary()
        
        assert "Cleanvid Configuration" in summary
        assert "Processing:" in summary
        assert "Paths:" in summary
        assert "OpenSubtitles:" in summary
        assert "FFmpeg:" in summary
        assert str(settings.processing.max_daily_processing) in summary
    
    def test_repr(self, tmp_path):
        """Test ConfigManager representation."""
        config_dir = tmp_path / "config"
        manager = ConfigManager(config_dir=config_dir)
        
        repr_str = repr(manager)
        assert "ConfigManager" in repr_str
        assert str(config_dir) in repr_str
        assert "loaded=False" in repr_str
        
        # Load settings
        manager.get_settings()
        repr_str = repr(manager)
        assert "loaded=True" in repr_str


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager."""
    
    def test_complete_workflow(self, tmp_path):
        """Test complete config management workflow."""
        config_dir = tmp_path / "config"
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        logs_dir = tmp_path / "logs"
        
        # Create directories
        for d in [input_dir, output_dir, logs_dir]:
            d.mkdir(parents=True)
        
        # Initialize manager
        manager = ConfigManager(config_dir=config_dir)
        manager.initialize_config_directory()
        
        # Load settings
        settings = manager.get_settings()
        
        # Modify settings
        settings.paths.input_dir = input_dir
        settings.paths.output_dir = output_dir
        settings.paths.logs_dir = logs_dir
        settings.processing.max_daily_processing = 10
        
        # Save
        manager.save_settings(settings)
        
        # Validate
        is_valid, errors = manager.validate_config()
        assert is_valid is True
        
        # Get summary
        summary = manager.get_config_summary()
        assert "10" in summary  # max_daily_processing
        
        # Reload and verify persistence
        manager2 = ConfigManager(config_dir=config_dir)
        settings2 = manager2.load_settings()
        assert settings2.processing.max_daily_processing == 10
        assert settings2.paths.input_dir == input_dir
