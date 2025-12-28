"""
Configuration management service.

Handles loading, saving, and validation of configuration files.
"""

import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from cleanvid.models.config import Settings


class ConfigManager:
    """
    Manages application configuration.
    
    Handles loading configuration from JSON files, validating settings,
    and initializing default configuration files when needed.
    """
    
    DEFAULT_CONFIG_FILENAME = "settings.json"
    TEMPLATE_SUFFIX = ".template"
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize ConfigManager.
        
        Args:
            config_dir: Directory containing configuration files.
                       If None, uses default from Settings.
        """
        self.config_dir = config_dir or Path("/config")
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILENAME
        self._settings: Optional[Settings] = None
    
    def load_settings(self, create_if_missing: bool = True) -> Settings:
        """
        Load settings from configuration file.
        
        Args:
            create_if_missing: If True, creates default config if not found.
        
        Returns:
            Settings object with validated configuration.
        
        Raises:
            FileNotFoundError: If config file not found and create_if_missing is False.
            ValueError: If configuration is invalid.
        """
        if not self.config_file.exists():
            if create_if_missing:
                self._create_default_config()
            else:
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_file}"
                )
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate and create Settings object
            self._settings = Settings(**config_data)
            return self._settings
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")
    
    def save_settings(self, settings: Settings) -> None:
        """
        Save settings to configuration file.
        
        Args:
            settings: Settings object to save.
        
        Raises:
            IOError: If unable to write configuration file.
        """
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert settings to dict
            config_data = self._settings_to_dict(settings)
            
            # Write to file with pretty formatting
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            self._settings = settings
        
        except Exception as e:
            raise IOError(f"Failed to save configuration: {e}")
    
    def get_settings(self) -> Settings:
        """
        Get current settings (loads if not already loaded).
        
        Returns:
            Current Settings object.
        """
        if self._settings is None:
            self._settings = self.load_settings()
        return self._settings
    
    def reload_settings(self) -> Settings:
        """
        Force reload settings from disk.
        
        Returns:
            Reloaded Settings object.
        """
        self._settings = None
        return self.load_settings()
    
    def initialize_config_directory(self) -> None:
        """
        Initialize configuration directory with all required files.
        
        Creates:
        - Config directory structure
        - Default settings.json
        - Profanity word list
        - Processed log file
        - README with documentation
        """
        # Create directory structure
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create settings file if needed
        if not self.config_file.exists():
            self._create_default_config()
        
        # Initialize other config files
        self._initialize_word_list()
        self._initialize_processed_log()
        self._create_readme()
    
    def _create_default_config(self) -> None:
        """Create default configuration file from template."""
        template_dir = Path(__file__).parent.parent.parent / "config"
        template_file = template_dir / f"{self.DEFAULT_CONFIG_FILENAME}{self.TEMPLATE_SUFFIX}"
        
        if template_file.exists():
            # Copy template
            shutil.copy(template_file, self.config_file)
        else:
            # Create from Settings defaults
            default_settings = Settings()
            self.save_settings(default_settings)
    
    def _initialize_word_list(self) -> None:
        """Initialize profanity word list file."""
        word_list_path = self.config_dir / "profanity_words.txt"
        
        if word_list_path.exists():
            return  # Don't overwrite existing list
        
        template_dir = Path(__file__).parent.parent.parent / "config"
        template_file = template_dir / f"profanity_words.txt{self.TEMPLATE_SUFFIX}"
        
        if template_file.exists():
            shutil.copy(template_file, word_list_path)
        else:
            # Create minimal word list
            default_words = [
                "# Profanity Word List",
                "# One word per line, # for comments",
                "",
                "damn",
                "hell",
                "shit",
                "fuck",
                "ass",
                "bitch",
            ]
            word_list_path.write_text("\n".join(default_words), encoding='utf-8')
    
    def _initialize_processed_log(self) -> None:
        """Initialize processed videos log file."""
        log_path = self.config_dir / "processed_log.json"
        
        if log_path.exists():
            return  # Don't overwrite existing log
        
        # Create empty log
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)
    
    def _create_readme(self) -> None:
        """Create README file in config directory."""
        readme_path = self.config_dir / "README.md"
        
        if readme_path.exists():
            return  # Don't overwrite existing README
        
        readme_content = """# Cleanvid Configuration

This directory contains configuration files for Cleanvid.

## Files

### settings.json
Main configuration file containing all application settings.

### profanity_words.txt
List of words to detect and mute. One word per line.
Lines starting with # are comments.

### processed_log.json
Tracks which videos have been processed. Used to avoid reprocessing.

## Configuration Options

### Processing
- `max_daily_processing`: Maximum number of videos to process per run
- `video_extensions`: File extensions to process
- `mute_padding_before_ms`: Padding before detected word (milliseconds)
- `mute_padding_after_ms`: Padding after detected word (milliseconds)

### Paths
- `input_dir`: Directory containing original videos
- `output_dir`: Directory for filtered videos
- `config_dir`: This directory
- `logs_dir`: Directory for application logs

### OpenSubtitles
- `enabled`: Whether to auto-download subtitles
- `language`: Subtitle language code (e.g., "en")
- `username`: OpenSubtitles username (optional)
- `password`: OpenSubtitles password (optional)
- `api_key`: OpenSubtitles API key (optional)

### FFmpeg
- `threads`: Number of CPU threads to use
- `audio_codec`: Audio codec for output (e.g., "aac")
- `audio_bitrate`: Audio bitrate (e.g., "192k")
- `re_encode_video`: Whether to re-encode video (slower but smaller)
- `video_codec`: Video codec if re-encoding (e.g., "libx264")
- `video_crf`: Video quality if re-encoding (0-51, lower is better)

## Modifying Configuration

1. Edit settings.json with your preferred text editor
2. Restart the application for changes to take effect
3. Invalid configuration will prevent startup

## Backup

Consider backing up your configuration periodically:
```bash
cp settings.json settings.json.backup
cp profanity_words.txt profanity_words.txt.backup
```
"""
        readme_path.write_text(readme_content, encoding='utf-8')
    
    def _settings_to_dict(self, settings: Settings) -> Dict[str, Any]:
        """
        Convert Settings object to dictionary for JSON serialization.
        
        Args:
            settings: Settings object to convert.
        
        Returns:
            Dictionary representation of settings.
        """
        return {
            "processing": {
                "max_daily_processing": settings.processing.max_daily_processing,
                "max_processing_time_minutes": settings.processing.max_processing_time_minutes,
                "video_extensions": settings.processing.video_extensions,
                "mute_padding_before_ms": settings.processing.mute_padding_before_ms,
                "mute_padding_after_ms": settings.processing.mute_padding_after_ms,
            },
            "paths": {
                "input_dir": str(settings.paths.input_dir),
                "output_dir": str(settings.paths.output_dir),
                "config_dir": str(settings.paths.config_dir),
                "logs_dir": str(settings.paths.logs_dir),
            },
            "opensubtitles": {
                "enabled": settings.opensubtitles.enabled,
                "language": settings.opensubtitles.language,
                "username": settings.opensubtitles.username,
                "password": settings.opensubtitles.password,
                "api_key": settings.opensubtitles.api_key,
            },
            "ffmpeg": {
                "threads": settings.ffmpeg.threads,
                "audio_codec": settings.ffmpeg.audio_codec,
                "audio_bitrate": settings.ffmpeg.audio_bitrate,
                "re_encode_video": settings.ffmpeg.re_encode_video,
                "video_codec": settings.ffmpeg.video_codec,
                "video_crf": settings.ffmpeg.video_crf,
            },
        }
    
    def validate_config(self) -> tuple[bool, list[str]]:
        """
        Validate current configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors = []
        
        try:
            settings = self.get_settings()
            
            # Check paths exist or can be created
            for path_name, path_value in [
                ("input_dir", settings.paths.input_dir),
                ("output_dir", settings.paths.output_dir),
                ("config_dir", settings.paths.config_dir),
                ("logs_dir", settings.paths.logs_dir),
            ]:
                if not path_value.exists():
                    errors.append(f"{path_name} does not exist: {path_value}")
            
            # Check word list exists
            word_list = settings.get_word_list_path()
            if not word_list.exists():
                errors.append(f"Word list not found: {word_list}")
            
            # Validate OpenSubtitles credentials if enabled
            if settings.opensubtitles.enabled:
                if not settings.opensubtitles.username and not settings.opensubtitles.api_key:
                    errors.append(
                        "OpenSubtitles enabled but no username or API key provided"
                    )
        
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
        
        return (len(errors) == 0, errors)
    
    def get_config_summary(self) -> str:
        """
        Get human-readable summary of current configuration.
        
        Returns:
            Formatted configuration summary.
        """
        settings = self.get_settings()
        
        summary = [
            "=== Cleanvid Configuration ===",
            "",
            "Processing:",
            f"  Max daily videos: {settings.processing.max_daily_processing}",
            f"  Video extensions: {', '.join(settings.processing.video_extensions)}",
            f"  Mute padding: {settings.processing.mute_padding_before_ms}ms before, "
            f"{settings.processing.mute_padding_after_ms}ms after",
            "",
            "Paths:",
            f"  Input:  {settings.paths.input_dir}",
            f"  Output: {settings.paths.output_dir}",
            f"  Config: {settings.paths.config_dir}",
            f"  Logs:   {settings.paths.logs_dir}",
            "",
            "OpenSubtitles:",
            f"  Enabled: {settings.opensubtitles.enabled}",
            f"  Language: {settings.opensubtitles.language}",
            f"  Authenticated: {bool(settings.opensubtitles.username or settings.opensubtitles.api_key)}",
            "",
            "FFmpeg:",
            f"  Threads: {settings.ffmpeg.threads}",
            f"  Audio: {settings.ffmpeg.audio_codec} @ {settings.ffmpeg.audio_bitrate}",
            f"  Re-encode video: {settings.ffmpeg.re_encode_video}",
        ]
        
        return "\n".join(summary)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"ConfigManager(config_dir={self.config_dir}, loaded={self._settings is not None})"
