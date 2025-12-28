"""
Unit tests for Processor service.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from cleanvid.services.processor import Processor
from cleanvid.models.processing import ProcessingResult, ProcessingStatus, ProcessingStats


@pytest.fixture
def test_environment(tmp_path):
    """Create complete test environment."""
    # Create directory structure
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    config_dir = tmp_path / "config"
    logs_dir = tmp_path / "logs"
    
    for d in [input_dir, output_dir, config_dir, logs_dir]:
        d.mkdir()
    
    # Create test video files
    video1 = input_dir / "movie1.mkv"
    video2 = input_dir / "movie2.mp4"
    video1.write_text("fake video 1")
    video2.write_text("fake video 2")
    
    # Create word list
    word_list = config_dir / "profanity_words.txt"
    word_list.write_text("damn\nhell\nshit\n")
    
    # Create settings file
    settings = config_dir / "settings.json"
    settings.write_text(f"""{{
        "processing": {{
            "max_daily_processing": 10,
            "video_extensions": [".mkv", ".mp4"],
            "mute_padding_before_ms": 500,
            "mute_padding_after_ms": 500
        }},
        "paths": {{
            "input_dir": "{str(input_dir)}",
            "output_dir": "{str(output_dir)}",
            "config_dir": "{str(config_dir)}",
            "logs_dir": "{str(logs_dir)}"
        }},
        "opensubtitles": {{
            "enabled": false,
            "language": "en",
            "username": null,
            "password": null,
            "api_key": null
        }},
        "ffmpeg": {{
            "threads": 2,
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            "re_encode_video": false,
            "video_codec": null,
            "video_crf": 23
        }}
    }}""")
    
    return {
        'root': tmp_path,
        'input': input_dir,
        'output': output_dir,
        'config': config_dir,
        'logs': logs_dir,
        'videos': [video1, video2],
    }


class TestProcessor:
    """Test Processor service."""
    
    def test_init(self, test_environment):
        """Test processor initialization."""
        processor = Processor(config_path=test_environment['config'])
        
        assert processor.settings is not None
        assert processor.file_manager is not None
        assert processor.subtitle_manager is not None
        assert processor.profanity_detector is not None
        assert processor.video_processor is not None
    
    def test_get_status(self, test_environment):
        """Test getting status."""
        processor = Processor(config_path=test_environment['config'])
        
        status = processor.get_status()
        
        assert 'config_valid' in status
        assert 'ffmpeg_available' in status
        assert 'total_videos' in status
        assert status['total_videos'] == 2
        assert status['unprocessed_videos'] == 2
    
    def test_print_status(self, test_environment, capsys):
        """Test printing status."""
        processor = Processor(config_path=test_environment['config'])
        
        processor.print_status()
        
        captured = capsys.readouterr()
        assert "Cleanvid Status" in captured.out
        assert "Videos:" in captured.out
    
    @patch('cleanvid.services.video_processor.VideoProcessor.process_video')
    def test_process_single(self, mock_process, test_environment):
        """Test processing single video."""
        # Mock successful processing
        result = ProcessingResult(
            video_path=test_environment['videos'][0],
            status=ProcessingStatus.SUCCESS,
            start_time=Mock(),
            segments_muted=5
        )
        result.mark_complete(success=True)
        mock_process.return_value = result
        
        processor = Processor(config_path=test_environment['config'])
        stats = processor.process_single(test_environment['videos'][0])
        
        assert stats.successful == 1
        assert stats.total_videos == 1
    
    @patch('cleanvid.services.video_processor.VideoProcessor.process_video')
    def test_process_batch(self, mock_process, test_environment):
        """Test batch processing."""
        # Mock successful processing
        def mock_process_func(video_path, **kwargs):
            result = ProcessingResult(
                video_path=video_path,
                status=ProcessingStatus.SUCCESS,
                start_time=Mock(),
                segments_muted=5
            )
            result.mark_complete(success=True)
            return result
        
        mock_process.side_effect = mock_process_func
        
        processor = Processor(config_path=test_environment['config'])
        stats = processor.process_batch(max_videos=2)
        
        assert stats.successful == 2
        assert stats.total_videos == 2
        assert mock_process.call_count == 2
    
    def test_get_recent_history(self, test_environment):
        """Test getting recent processing history."""
        processor = Processor(config_path=test_environment['config'])
        
        # Initially empty
        history = processor.get_recent_history()
        assert len(history) == 0
        
        # Mark a video as processed
        processor.file_manager.mark_as_processed(
            test_environment['videos'][0],
            success=True,
            segments_muted=5
        )
        
        history = processor.get_recent_history()
        assert len(history) == 1
    
    def test_reset_video(self, test_environment):
        """Test resetting video status."""
        processor = Processor(config_path=test_environment['config'])
        
        video = test_environment['videos'][0]
        
        # Mark as processed
        processor.file_manager.mark_as_processed(video, success=True)
        assert processor.file_manager.is_processed(video)
        
        # Reset
        result = processor.reset_video(video)
        
        assert result is True
        assert not processor.file_manager.is_processed(video)
    
    def test_reload_config(self, test_environment):
        """Test reloading configuration."""
        processor = Processor(config_path=test_environment['config'])
        
        old_max_daily = processor.settings.processing.max_daily_processing
        
        # Modify settings file
        import json
        settings_file = test_environment['config'] / "settings.json"
        with open(settings_file, 'r') as f:
            settings_data = json.load(f)
        
        settings_data['processing']['max_daily_processing'] = 20
        
        with open(settings_file, 'w') as f:
            json.dump(settings_data, f)
        
        # Reload
        processor.reload_config()
        
        assert processor.settings.processing.max_daily_processing == 20
        assert processor.settings.processing.max_daily_processing != old_max_daily
    
    def test_repr(self, test_environment):
        """Test representation."""
        processor = Processor(config_path=test_environment['config'])
        
        repr_str = repr(processor)
        assert "Processor" in repr_str
    
    def test_str(self, test_environment):
        """Test string representation."""
        processor = Processor(config_path=test_environment['config'])
        
        str_rep = str(processor)
        assert "Processor" in str_rep
        assert "pending" in str_rep


class TestProcessorIntegration:
    """Integration tests for Processor."""
    
    @patch('cleanvid.utils.ffmpeg_wrapper.FFmpegWrapper.check_available')
    def test_status_includes_ffmpeg_check(self, mock_check, test_environment):
        """Test status includes FFmpeg availability."""
        mock_check.return_value = (True, "ffmpeg version 4.4.1")
        
        processor = Processor(config_path=test_environment['config'])
        status = processor.get_status()
        
        assert status['ffmpeg_available'] is True
        assert "ffmpeg version" in status['ffmpeg_version']
    
    @patch('cleanvid.services.video_processor.VideoProcessor.process_video')
    def test_process_batch_time_limit(self, mock_process, test_environment):
        """Test batch processing with time limit."""
        from datetime import timedelta
        from unittest.mock import Mock
        
        # Mock slow processing (each video takes time)
        def slow_process(video_path, **kwargs):
            import time
            time.sleep(0.1)  # Simulate processing time
            result = ProcessingResult(
                video_path=video_path,
                status=ProcessingStatus.SUCCESS,
                start_time=Mock(),
                segments_muted=5
            )
            result.mark_complete(success=True)
            return result
        
        mock_process.side_effect = slow_process
        
        processor = Processor(config_path=test_environment['config'])
        
        # Set very short time limit
        stats = processor.process_batch(
            max_videos=100,  # High number
            max_time_minutes=0.05  # 3 seconds (0.05 * 60 = 3s)
        )
        
        # Should process fewer than 100 due to time limit
        assert stats.total_videos < 100
        assert stats.total_videos > 0  # But should process at least one
