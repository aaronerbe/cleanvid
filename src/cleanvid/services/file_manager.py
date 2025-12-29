"""
File management service.

Handles video file discovery, output path generation, and processed file tracking.
"""

import json
from pathlib import Path
from typing import List, Set, Optional, Dict, Any
from datetime import datetime

from cleanvid.models.config import PathConfig, ProcessingConfig


class FileManager:
    """
    Manages file operations for video processing.
    
    Handles video file discovery, output path generation, and tracking
    of which files have been processed.
    """
    
    def __init__(
        self,
        path_config: PathConfig,
        processing_config: ProcessingConfig
    ):
        """
        Initialize FileManager.
        
        Args:
            path_config: Path configuration.
            processing_config: Processing configuration.
        """
        self.path_config = path_config
        self.processing_config = processing_config
        self.processed_log_path = path_config.config_dir / "processed_log.json"
        self._processed_files: Set[str] = set()
        self._load_processed_log()
    
    def _load_processed_log(self) -> None:
        """Load processed files log from disk."""
        if not self.processed_log_path.exists():
            self._processed_files = set()
            return
        
        try:
            with open(self.processed_log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Extract file paths from log entries
                self._processed_files = {
                    entry['video_path'] for entry in data
                    if isinstance(entry, dict) and 'video_path' in entry
                }
        except Exception as e:
            print(f"Warning: Failed to load processed log: {e}")
            self._processed_files = set()
    
    def _save_processed_log(self) -> None:
        """Save processed files log to disk."""
        try:
            # Ensure config directory exists
            self.processed_log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing log to preserve metadata
            existing_log = []
            if self.processed_log_path.exists():
                try:
                    with open(self.processed_log_path, 'r', encoding='utf-8') as f:
                        existing_log = json.load(f)
                except:
                    existing_log = []
            
            # Write back to disk
            with open(self.processed_log_path, 'w', encoding='utf-8') as f:
                json.dump(existing_log, f, indent=2)
        
        except Exception as e:
            print(f"Warning: Failed to save processed log: {e}")
    
    def _is_synology_metadata_path(self, path: Path) -> bool:
        """
        Check if path is a Synology metadata directory or file.
        
        Synology creates @eaDir folders for thumbnails and metadata.
        These should never be processed as video files.
        
        Args:
            path: Path to check.
        
        Returns:
            True if path is Synology metadata, False otherwise.
        """
        path_str = str(path)
        
        # Check for @eaDir in path
        if '@eaDir' in path_str:
            return True
        
        # Check for other Synology metadata patterns
        synology_patterns = [
            '#recycle',      # Recycle bin
            '@tmp',          # Temp files
            '.@__thumb',     # Thumbnails
            'SYNOINDEX',     # Index files
        ]
        
        for pattern in synology_patterns:
            if pattern in path_str:
                return True
        
        return False
    
    def discover_videos(
        self,
        directory: Optional[Path] = None,
        recursive: bool = True,
        extensions: Optional[List[str]] = None
    ) -> List[Path]:
        """
        Discover video files in directory.
        
        Automatically filters out Synology metadata folders like @eaDir.
        
        Args:
            directory: Directory to search. If None, uses input_dir from config.
            recursive: If True, searches subdirectories.
            extensions: File extensions to match. If None, uses config extensions.
        
        Returns:
            List of video file paths (excluding Synology metadata).
        """
        if directory is None:
            directory = self.path_config.input_dir
        
        if extensions is None:
            extensions = self.processing_config.video_extensions
        
        if not directory.exists():
            return []
        
        video_files = []
        
        if recursive:
            # Recursively search for videos
            for ext in extensions:
                # Use rglob for recursive search
                for video_path in directory.rglob(f"*{ext}"):
                    # Skip Synology metadata paths
                    if self._is_synology_metadata_path(video_path):
                        continue
                    video_files.append(video_path)
        else:
            # Only search immediate directory
            for ext in extensions:
                for video_path in directory.glob(f"*{ext}"):
                    # Skip Synology metadata paths
                    if self._is_synology_metadata_path(video_path):
                        continue
                    video_files.append(video_path)
        
        # Sort for consistent ordering
        return sorted(video_files)
    
    def get_unprocessed_videos(
        self,
        directory: Optional[Path] = None,
        recursive: bool = True
    ) -> List[Path]:
        """
        Get list of videos that haven't been processed yet.
        
        Args:
            directory: Directory to search. If None, uses input_dir.
            recursive: If True, searches subdirectories.
        
        Returns:
            List of unprocessed video file paths.
        """
        all_videos = self.discover_videos(directory, recursive)
        
        # Filter out already processed files
        unprocessed = [
            video for video in all_videos
            if str(video) not in self._processed_files
        ]
        
        return unprocessed
    
    def generate_output_path(
        self,
        input_path: Path,
        preserve_structure: bool = True
    ) -> Path:
        """
        Generate output path for a video file.
        
        Args:
            input_path: Input video file path.
            preserve_structure: If True, preserves directory structure from input.
        
        Returns:
            Output file path.
        """
        if preserve_structure:
            # Get relative path from input directory
            try:
                relative_path = input_path.relative_to(self.path_config.input_dir)
            except ValueError:
                # If input is not under input_dir, just use filename
                relative_path = input_path.name
            
            # Construct output path preserving structure
            output_path = self.path_config.output_dir / relative_path
        else:
            # Just use filename in output directory
            output_path = self.path_config.output_dir / input_path.name
        
        return output_path
    
    def mark_as_processed(
        self,
        video_path: Path,
        success: bool,
        segments_muted: int = 0,
        error: Optional[str] = None
    ) -> None:
        """
        Mark a video as processed.
        
        Args:
            video_path: Path to video file.
            success: Whether processing was successful.
            segments_muted: Number of segments that were muted.
            error: Error message if processing failed.
        """
        # Add to processed set
        self._processed_files.add(str(video_path))
        
        # Load existing log
        log_entries = []
        if self.processed_log_path.exists():
            try:
                with open(self.processed_log_path, 'r', encoding='utf-8') as f:
                    log_entries = json.load(f)
            except:
                log_entries = []
        
        # Add new entry
        entry = {
            'video_path': str(video_path),
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'segments_muted': segments_muted,
            'error': error
        }
        log_entries.append(entry)
        
        # Save log
        try:
            self.processed_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.processed_log_path, 'w', encoding='utf-8') as f:
                json.dump(log_entries, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save processed log: {e}")
    
    def is_processed(self, video_path: Path) -> bool:
        """
        Check if a video has been processed.
        
        Args:
            video_path: Path to video file.
        
        Returns:
            True if video has been processed, False otherwise.
        """
        return str(video_path) in self._processed_files
    
    def get_processed_count(self) -> int:
        """Get count of processed videos."""
        return len(self._processed_files)
    
    def get_processing_history(
        self,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get processing history.
        
        Args:
            limit: Maximum number of entries to return. If None, returns all.
        
        Returns:
            List of processing log entries, newest first.
        """
        if not self.processed_log_path.exists():
            return []
        
        try:
            with open(self.processed_log_path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
            
            # Sort by timestamp, newest first
            entries.sort(
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )
            
            if limit:
                entries = entries[:limit]
            
            return entries
        
        except Exception as e:
            print(f"Warning: Failed to load processing history: {e}")
            return []
    
    def clear_processed_log(self) -> None:
        """Clear the processed files log."""
        self._processed_files.clear()
        
        if self.processed_log_path.exists():
            self.processed_log_path.unlink()
    
    def reset_processed_status(self, video_path: Path) -> bool:
        """
        Reset processed status for a specific video.
        
        Args:
            video_path: Path to video file.
        
        Returns:
            True if video was in processed list, False otherwise.
        """
        video_str = str(video_path)
        
        if video_str not in self._processed_files:
            return False
        
        # Remove from set
        self._processed_files.remove(video_str)
        
        # Remove from log file
        if self.processed_log_path.exists():
            try:
                with open(self.processed_log_path, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                
                # Filter out this video
                entries = [
                    e for e in entries
                    if e.get('video_path') != video_str
                ]
                
                # Save updated log
                with open(self.processed_log_path, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, indent=2)
            except Exception as e:
                print(f"Warning: Failed to update processed log: {e}")
        
        return True
    
    def reset_failed_videos(self) -> int:
        """
        Reset all failed videos so they can be reprocessed.
        
        Returns:
            Number of failed videos that were reset.
        """
        if not self.processed_log_path.exists():
            return 0
        
        try:
            with open(self.processed_log_path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
            
            # Separate failed and successful entries
            failed_entries = [e for e in entries if not e.get('success', True)]
            successful_entries = [e for e in entries if e.get('success', True)]
            
            # Remove failed videos from processed set
            for entry in failed_entries:
                video_path = entry.get('video_path')
                if video_path in self._processed_files:
                    self._processed_files.remove(video_path)
            
            # Save only successful entries
            with open(self.processed_log_path, 'w', encoding='utf-8') as f:
                json.dump(successful_entries, f, indent=2)
            
            return len(failed_entries)
        
        except Exception as e:
            print(f"Error resetting failed videos: {e}")
            return 0
    
    def get_failed_videos(self) -> List[Dict[str, Any]]:
        """
        Get list of videos that failed processing.
        
        Returns:
            List of failed video entries with details.
        """
        if not self.processed_log_path.exists():
            return []
        
        try:
            with open(self.processed_log_path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
            
            # Filter failed entries
            failed = [
                e for e in entries
                if not e.get('success', True)
            ]
            
            # Sort by timestamp, newest first
            failed.sort(
                key=lambda x: x.get('timestamp', ''),
                reverse=True
            )
            
            return failed
        
        except Exception as e:
            print(f"Warning: Failed to load failed videos: {e}")
            return []
    
    def get_file_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about files.
        
        Returns:
            Dictionary with file statistics.
        """
        all_videos = self.discover_videos()
        unprocessed = self.get_unprocessed_videos()
        
        # Calculate total size
        total_size = sum(
            video.stat().st_size for video in all_videos
            if video.exists()
        )
        
        unprocessed_size = sum(
            video.stat().st_size for video in unprocessed
            if video.exists()
        )
        
        return {
            'total_videos': len(all_videos),
            'processed_videos': len(self._processed_files),
            'unprocessed_videos': len(unprocessed),
            'total_size_gb': total_size / (1024**3),
            'unprocessed_size_gb': unprocessed_size / (1024**3),
            'input_directory': str(self.path_config.input_dir),
            'output_directory': str(self.path_config.output_dir),
        }
    
    def ensure_output_directory(self, output_path: Path) -> None:
        """
        Ensure output directory exists.
        
        Args:
            output_path: Output file path.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"FileManager(input_dir={self.path_config.input_dir}, "
            f"output_dir={self.path_config.output_dir}, "
            f"processed={len(self._processed_files)})"
        )
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"FileManager: {len(self._processed_files)} processed, "
            f"{len(self.get_unprocessed_videos())} pending"
        )
