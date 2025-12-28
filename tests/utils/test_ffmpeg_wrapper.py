"""
Unit tests for FFmpeg wrapper.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
from subprocess import CalledProcessError
from cleanvid.utils.ffmpeg_wrapper import FFmpegWrapper, FFprobeResult


class TestFFmpegWrapper:
    """Test FFmpegWrapper class."""
    
    def test_init_default(self):
        """Test initialization with defaults."""
        wrapper = FFmpegWrapper()
        
        assert wrapper.ffmpeg_path == 'ffmpeg'
        assert wrapper.ffprobe_path == 'ffprobe'
    
    def test_init_custom_paths(self):
        """Test initialization with custom paths."""
        wrapper = FFmpegWrapper(
            ffmpeg_path='/usr/bin/ffmpeg',
            ffprobe_path='/usr/bin/ffprobe'
        )
        
        assert wrapper.ffmpeg_path == '/usr/bin/ffmpeg'
        assert wrapper.ffprobe_path == '/usr/bin/ffprobe'
    
    @patch('subprocess.run')
    def test_probe_success(self, mock_run, tmp_path):
        """Test successful video probing."""
        video_file = tmp_path / "test.mkv"
        video_file.write_text("fake video")
        
        # Mock ffprobe response
        ffprobe_output = {
            "format": {
                "duration": "7200.50",
                "size": "1073741824",
                "bit_rate": "1000000",
                "format_name": "matroska,webm"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "24000/1001"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2
                }
            ]
        }
        
        mock_run.return_value = Mock(
            stdout=json.dumps(ffprobe_output),
            returncode=0
        )
        
        wrapper = FFmpegWrapper()
        result = wrapper.probe(video_file)
        
        assert isinstance(result, FFprobeResult)
        assert result.path == video_file
        assert result.duration == 7200.5
        assert result.size == 1073741824
        assert result.video_codec == 'h264'
        assert result.audio_codec == 'aac'
        assert result.width == 1920
        assert result.height == 1080
        assert result.audio_sample_rate == 48000
        assert result.audio_channels == 2
    
    def test_probe_missing_file(self):
        """Test probing non-existent file."""
        wrapper = FFmpegWrapper()
        
        with pytest.raises(FileNotFoundError):
            wrapper.probe(Path("/nonexistent/video.mkv"))
    
    @patch('subprocess.run')
    def test_check_available_success(self, mock_run):
        """Test FFmpeg availability check success."""
        mock_run.return_value = Mock(
            stdout="ffmpeg version 4.4.1\n...",
            returncode=0
        )
        
        wrapper = FFmpegWrapper()
        is_available, version = wrapper.check_available()
        
        assert is_available is True
        assert "ffmpeg version" in version
    
    @patch('subprocess.run')
    def test_check_available_not_found(self, mock_run):
        """Test FFmpeg not available."""
        mock_run.side_effect = FileNotFoundError()
        
        wrapper = FFmpegWrapper()
        is_available, version = wrapper.check_available()
        
        assert is_available is False
        assert "not found" in version
    
    @patch('subprocess.run')
    def test_mute_audio_success(self, mock_run, tmp_path):
        """Test successful audio muting."""
        input_file = tmp_path / "input.mkv"
        output_file = tmp_path / "output.mkv"
        input_file.write_text("fake video")
        
        mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
        
        wrapper = FFmpegWrapper()
        result = wrapper.mute_audio(
            input_path=input_file,
            output_path=output_file,
            filter_chain="volume=0"
        )
        
        assert result is True
        mock_run.assert_called_once()
        
        # Check command includes expected arguments
        call_args = mock_run.call_args[0][0]
        assert '-af' in call_args
        assert 'volume=0' in call_args
        assert str(input_file) in call_args
        assert str(output_file) in call_args


class TestFFprobeResult:
    """Test FFprobeResult dataclass."""
    
    def test_create_full(self, tmp_path):
        """Test creating FFprobeResult with all fields."""
        video_file = tmp_path / "test.mkv"
        
        result = FFprobeResult(
            path=video_file,
            format="matroska",
            duration=7200.5,
            size=1073741824,
            bit_rate=1000000,
            video_codec="h264",
            audio_codec="aac",
            width=1920,
            height=1080,
            frame_rate=23.976,
            audio_sample_rate=48000,
            audio_channels=2
        )
        
        assert result.path == video_file
        assert result.format == "matroska"
        assert result.duration == 7200.5
        assert result.video_codec == "h264"
        assert result.width == 1920
