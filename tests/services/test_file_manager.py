"""
Unit tests for FileManager service.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from cleanvid.services.file_manager import FileManager
from cleanvid.models.config import PathConfig, ProcessingConfig


@pytest.fixture
def file_structure(tmp_path):
    """Create a test file structure."""
    # Create input directory structure
    input_dir = tmp_path / "input"
    action_dir = input_dir / "Action"
    comedy_dir = input_dir / "Comedy"
    
    action_dir.mkdir(parents=True)
    comedy_dir.mkdir(parents=True)
    
    # Create video files
    videos = {
        'action1': action_dir / "movie1.mkv",
        'action2': action_dir / "movie2.mp4",
        'comedy1': comedy_dir / "funny1.mkv",
        'comedy2': comedy_dir / "funny2.avi",
        'root': input_dir / "root_movie.mov",
    }
    
    for video in videos.values():
        video.write_text("fake video content")
    
    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Create config directory
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    return {
        'root': tmp_path,
        'input': input_dir,
        'output': output_dir,
        'config': config_dir,
        'videos': videos,
    }


@pytest.fixture
def file_manager(file_structure):
    """Create FileManager with test directories."""
    path_config = PathConfig(
        input_dir=file_structure['input'],
        output_dir=file_structure['output'],
        config_dir=file_structure['config'],
        logs_dir=file_structure['root'] / "logs"
    )
    
    processing_config = ProcessingConfig()
    
    return FileManager(
        path_config=path_config,
        processing_config=processing_config
    )


class TestFileManager:
    """Test FileManager service."""
    
    def test_init(self, file_manager, file_structure):
        """Test initialization."""
        assert file_manager.path_config.input_dir == file_structure['input']
        assert file_manager.path_config.output_dir == file_structure['output']
        assert len(file_manager._processed_files) == 0
    
    def test_discover_videos_recursive(self, file_manager, file_structure):
        """Test recursive video discovery."""
        videos = file_manager.discover_videos()
        
        assert len(videos) == 5  # All videos
        assert all(isinstance(v, Path) for v in videos)
        assert all(v.exists() for v in videos)
    
    def test_discover_videos_non_recursive(self, file_manager, file_structure):
        """Test non-recursive video discovery."""
        videos = file_manager.discover_videos(recursive=False)
        
        # Only root level video
        assert len(videos) == 1
        assert videos[0].name == "root_movie.mov"
    
    def test_discover_videos_specific_directory(self, file_manager, file_structure):
        """Test discovery in specific directory."""
        action_dir = file_structure['input'] / "Action"
        videos = file_manager.discover_videos(directory=action_dir)
        
        assert len(videos) == 2
        assert all("Action" in str(v) for v in videos)
    
    def test_discover_videos_specific_extensions(self, file_manager, file_structure):
        """Test discovery with specific extensions."""
        videos = file_manager.discover_videos(extensions=['.mkv'])
        
        assert len(videos) == 2  # Only .mkv files
        assert all(v.suffix == '.mkv' for v in videos)
    
    def test_discover_videos_empty_directory(self, tmp_path):
        """Test discovery in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        path_config = PathConfig(
            input_dir=empty_dir,
            output_dir=tmp_path / "output",
            config_dir=tmp_path / "config",
            logs_dir=tmp_path / "logs"
        )
        
        manager = FileManager(path_config, ProcessingConfig())
        videos = manager.discover_videos()
        
        assert len(videos) == 0
    
    def test_get_unprocessed_videos_all(self, file_manager):
        """Test getting unprocessed videos when none processed."""
        unprocessed = file_manager.get_unprocessed_videos()
        
        assert len(unprocessed) == 5  # All videos
    
    def test_get_unprocessed_videos_some_processed(self, file_manager, file_structure):
        """Test getting unprocessed videos after marking some processed."""
        # Mark one as processed
        video = file_structure['videos']['action1']
        file_manager.mark_as_processed(video, success=True, segments_muted=5)
        
        unprocessed = file_manager.get_unprocessed_videos()
        
        assert len(unprocessed) == 4
        assert video not in unprocessed
    
    def test_generate_output_path_preserve_structure(self, file_manager, file_structure):
        """Test output path generation preserving structure."""
        input_video = file_structure['videos']['action1']
        
        output_path = file_manager.generate_output_path(
            input_video,
            preserve_structure=True
        )
        
        # Should preserve "Action" subdirectory
        assert "Action" in str(output_path)
        assert output_path.name == input_video.name
        assert file_structure['output'] in output_path.parents
    
    def test_generate_output_path_flat(self, file_manager, file_structure):
        """Test output path generation without preserving structure."""
        input_video = file_structure['videos']['action1']
        
        output_path = file_manager.generate_output_path(
            input_video,
            preserve_structure=False
        )
        
        # Should be directly in output directory
        assert output_path.parent == file_structure['output']
        assert output_path.name == input_video.name
    
    def test_mark_as_processed_success(self, file_manager, file_structure):
        """Test marking video as processed successfully."""
        video = file_structure['videos']['action1']
        
        file_manager.mark_as_processed(
            video,
            success=True,
            segments_muted=10
        )
        
        assert file_manager.is_processed(video)
        assert file_manager.get_processed_count() == 1
    
    def test_mark_as_processed_failure(self, file_manager, file_structure):
        """Test marking video as processed with failure."""
        video = file_structure['videos']['action1']
        
        file_manager.mark_as_processed(
            video,
            success=False,
            error="FFmpeg failed"
        )
        
        assert file_manager.is_processed(video)
        
        # Check log entry
        history = file_manager.get_processing_history(limit=1)
        assert len(history) == 1
        assert history[0]['success'] is False
        assert history[0]['error'] == "FFmpeg failed"
    
    def test_mark_as_processed_creates_log(self, file_manager, file_structure):
        """Test that marking as processed creates log file."""
        video = file_structure['videos']['action1']
        
        file_manager.mark_as_processed(video, success=True, segments_muted=5)
        
        assert file_manager.processed_log_path.exists()
        
        # Verify log content
        with open(file_manager.processed_log_path, 'r') as f:
            log_data = json.load(f)
        
        assert len(log_data) == 1
        assert log_data[0]['video_path'] == str(video)
        assert log_data[0]['success'] is True
        assert log_data[0]['segments_muted'] == 5
    
    def test_is_processed(self, file_manager, file_structure):
        """Test checking if video is processed."""
        video = file_structure['videos']['action1']
        
        assert file_manager.is_processed(video) is False
        
        file_manager.mark_as_processed(video, success=True)
        
        assert file_manager.is_processed(video) is True
    
    def test_get_processed_count(self, file_manager, file_structure):
        """Test getting processed count."""
        assert file_manager.get_processed_count() == 0
        
        file_manager.mark_as_processed(file_structure['videos']['action1'], True)
        assert file_manager.get_processed_count() == 1
        
        file_manager.mark_as_processed(file_structure['videos']['action2'], True)
        assert file_manager.get_processed_count() == 2
    
    def test_get_processing_history(self, file_manager, file_structure):
        """Test getting processing history."""
        # Mark multiple videos as processed
        file_manager.mark_as_processed(
            file_structure['videos']['action1'],
            success=True,
            segments_muted=5
        )
        file_manager.mark_as_processed(
            file_structure['videos']['action2'],
            success=False,
            error="No subtitle"
        )
        
        history = file_manager.get_processing_history()
        
        assert len(history) == 2
        # Should be newest first
        assert history[0]['video_path'] == str(file_structure['videos']['action2'])
        assert history[1]['video_path'] == str(file_structure['videos']['action1'])
    
    def test_get_processing_history_limit(self, file_manager, file_structure):
        """Test getting limited processing history."""
        # Mark 3 videos as processed
        for video_key in ['action1', 'action2', 'comedy1']:
            file_manager.mark_as_processed(
                file_structure['videos'][video_key],
                success=True
            )
        
        history = file_manager.get_processing_history(limit=2)
        
        assert len(history) == 2
    
    def test_clear_processed_log(self, file_manager, file_structure):
        """Test clearing processed log."""
        # Mark some videos as processed
        file_manager.mark_as_processed(file_structure['videos']['action1'], True)
        file_manager.mark_as_processed(file_structure['videos']['action2'], True)
        
        assert file_manager.get_processed_count() == 2
        
        file_manager.clear_processed_log()
        
        assert file_manager.get_processed_count() == 0
        assert not file_manager.processed_log_path.exists()
    
    def test_reset_processed_status(self, file_manager, file_structure):
        """Test resetting processed status for a video."""
        video = file_structure['videos']['action1']
        
        file_manager.mark_as_processed(video, success=True)
        assert file_manager.is_processed(video) is True
        
        result = file_manager.reset_processed_status(video)
        
        assert result is True
        assert file_manager.is_processed(video) is False
    
    def test_reset_processed_status_not_processed(self, file_manager, file_structure):
        """Test resetting status for unprocessed video."""
        video = file_structure['videos']['action1']
        
        result = file_manager.reset_processed_status(video)
        
        assert result is False
    
    def test_get_file_statistics(self, file_manager):
        """Test getting file statistics."""
        stats = file_manager.get_file_statistics()
        
        assert stats['total_videos'] == 5
        assert stats['processed_videos'] == 0
        assert stats['unprocessed_videos'] == 5
        assert stats['total_size_gb'] > 0
        assert 'input_directory' in stats
        assert 'output_directory' in stats
    
    def test_get_file_statistics_with_processed(self, file_manager, file_structure):
        """Test statistics after processing some videos."""
        file_manager.mark_as_processed(file_structure['videos']['action1'], True)
        file_manager.mark_as_processed(file_structure['videos']['action2'], True)
        
        stats = file_manager.get_file_statistics()
        
        assert stats['total_videos'] == 5
        assert stats['processed_videos'] == 2
        assert stats['unprocessed_videos'] == 3
    
    def test_ensure_output_directory(self, file_manager, file_structure):
        """Test ensuring output directory exists."""
        output_path = file_structure['output'] / "subdir" / "another" / "file.mkv"
        
        assert not output_path.parent.exists()
        
        file_manager.ensure_output_directory(output_path)
        
        assert output_path.parent.exists()
    
    def test_persistence_across_instances(self, file_structure):
        """Test that processed log persists across FileManager instances."""
        path_config = PathConfig(
            input_dir=file_structure['input'],
            output_dir=file_structure['output'],
            config_dir=file_structure['config'],
            logs_dir=file_structure['root'] / "logs"
        )
        
        # First instance - mark video as processed
        manager1 = FileManager(path_config, ProcessingConfig())
        video = file_structure['videos']['action1']
        manager1.mark_as_processed(video, success=True, segments_muted=5)
        
        # Second instance - should load processed log
        manager2 = FileManager(path_config, ProcessingConfig())
        
        assert manager2.is_processed(video) is True
        assert manager2.get_processed_count() == 1
    
    def test_repr(self, file_manager, file_structure):
        """Test detailed representation."""
        repr_str = repr(file_manager)
        
        assert "FileManager" in repr_str
        assert str(file_structure['input']) in repr_str
        assert str(file_structure['output']) in repr_str
    
    def test_str(self, file_manager):
        """Test string representation."""
        str_rep = str(file_manager)
        
        assert "FileManager" in str_rep
        assert "processed" in str_rep
        assert "pending" in str_rep


class TestFileManagerEdgeCases:
    """Test edge cases in FileManager."""
    
    def test_load_corrupted_log(self, tmp_path):
        """Test handling corrupted processed log."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        # Create corrupted log
        log_file = config_dir / "processed_log.json"
        log_file.write_text("{ invalid json }")
        
        path_config = PathConfig(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            config_dir=config_dir,
            logs_dir=tmp_path / "logs"
        )
        
        # Should not crash, just use empty log
        manager = FileManager(path_config, ProcessingConfig())
        
        assert manager.get_processed_count() == 0
    
    def test_discover_videos_nonexistent_directory(self, tmp_path):
        """Test discovery in non-existent directory."""
        path_config = PathConfig(
            input_dir=tmp_path / "nonexistent",
            output_dir=tmp_path / "output",
            config_dir=tmp_path / "config",
            logs_dir=tmp_path / "logs"
        )
        
        manager = FileManager(path_config, ProcessingConfig())
        videos = manager.discover_videos()
        
        assert len(videos) == 0
    
    def test_generate_output_path_input_not_under_input_dir(self, file_manager, tmp_path):
        """Test output path generation for file outside input directory."""
        external_video = tmp_path / "external" / "video.mkv"
        external_video.parent.mkdir()
        external_video.write_text("fake video")
        
        output_path = file_manager.generate_output_path(
            external_video,
            preserve_structure=True
        )
        
        # Should just use filename
        assert output_path.name == external_video.name
