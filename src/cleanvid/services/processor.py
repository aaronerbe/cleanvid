"""
Main batch processing orchestrator.

Coordinates all services to process multiple videos with error handling and limits.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from cleanvid.models.config import Settings
from cleanvid.models.processing import ProcessingStats, ProcessingStatus
from cleanvid.services.config_manager import ConfigManager
from cleanvid.services.file_manager import FileManager
from cleanvid.services.subtitle_manager import SubtitleManager
from cleanvid.services.profanity_detector import ProfanityDetector
from cleanvid.services.video_processor import VideoProcessor


class Processor:
    """
    Main batch processing orchestrator.

    Coordinates all services to process videos in batch with proper
    error handling, daily limits, and progress tracking.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize Processor.

        Args:
            config_path: Path to config directory. If None, uses default.
        """
        # Load configuration
        self.config_manager = ConfigManager(config_dir=config_path)
        self.settings = self.config_manager.load_settings()

        # Initialize services
        self.file_manager = FileManager(
            path_config=self.settings.paths,
            processing_config=self.settings.processing
        )

        self.subtitle_manager = SubtitleManager(
            config=self.settings.opensubtitles
        )

        self.profanity_detector = ProfanityDetector(
            word_list_path=self.settings.get_word_list_path()
        )

        self.video_processor = VideoProcessor(
            subtitle_manager=self.subtitle_manager,
            profanity_detector=self.profanity_detector,
            ffmpeg_config=self.settings.ffmpeg
        )

    def process_batch(
        self,
        max_videos: Optional[int] = None,
        max_time_minutes: Optional[int] = None,
        force_reprocess: bool = False
    ) -> ProcessingStats:
        """
        Process a batch of videos.

        Args:
            max_videos: Maximum number of videos to process. If None, uses config.
            max_time_minutes: Maximum processing time in minutes. If None, uses config.
            force_reprocess: If True, reprocesses already processed videos.

        Returns:
            ProcessingStats with batch results.

        Note:
            Processing stops when EITHER max_videos OR max_time_minutes is reached.
        """
        if max_videos is None:
            max_videos = self.settings.processing.max_daily_processing

        if max_time_minutes is None:
            max_time_minutes = self.settings.processing.max_processing_time_minutes

        # Get videos to process
        if force_reprocess:
            videos = self.file_manager.discover_videos()
        else:
            videos = self.file_manager.get_unprocessed_videos()

        # Limit to max_videos (but may process fewer if time limit hit)
        videos = videos[:max_videos]

        # Initialize statistics
        stats = ProcessingStats(
            total_videos=len(videos),
            start_time=datetime.now()
        )

        print(f"\n{'='*60}")
        print(f"Starting batch processing of {len(videos)} videos")
        if max_time_minutes:
            print(f"Time limit: {max_time_minutes} minutes")
        print(f"{'='*60}\n")

        # Process each video
        for i, video_path in enumerate(videos, 1):
            # Check time limit
            if max_time_minutes:
                elapsed_minutes = (
                    datetime.now() - stats.start_time).total_seconds() / 60
                if elapsed_minutes >= max_time_minutes:
                    print(
                        f"\n⏱️  Time limit reached ({elapsed_minutes:.1f}/{max_time_minutes} minutes)")
                    print(
                        f"Stopping batch processing. Processed {i-1}/{len(videos)} videos.")
                    break

            print(f"\n[{i}/{len(videos)}] Processing: {video_path.name}")
            print(f"-" * 60)

            try:
                # Generate output path
                output_path = self.file_manager.generate_output_path(
                    video_path,
                    preserve_structure=True
                )

                # Ensure output directory exists
                self.file_manager.ensure_output_directory(output_path)

                # Process video
                result = self.video_processor.process_video(
                    video_path=video_path,
                    output_path=output_path,
                    mute_padding_before_ms=self.settings.processing.mute_padding_before_ms,
                    mute_padding_after_ms=self.settings.processing.mute_padding_after_ms,
                    auto_download_subtitles=self.settings.opensubtitles.enabled
                )

                # Add result to statistics
                stats.add_result(result)

                # Mark as processed
                self.file_manager.mark_as_processed(
                    video_path=video_path,
                    success=result.success,
                    segments_muted=result.segments_muted,
                    error=result.error_message
                )

                # Print summary
                summary = self.video_processor.get_processing_summary(result)
                print(summary)

            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                stats.failed += 1

                # Mark as processed with error
                self.file_manager.mark_as_processed(
                    video_path=video_path,
                    success=False,
                    error=str(e)
                )

        # Finalize statistics
        stats.mark_complete()

        print(f"\n{'='*60}")
        print("Batch Processing Complete")
        print(f"{'='*60}\n")
        print(stats.to_summary_string())

        return stats

    def process_single(self, video_path: Path) -> ProcessingStats:
        """
        Process a single video file.

        Args:
            video_path: Path to video file to process.

        Returns:
            ProcessingStats with single video result.
        """
        stats = ProcessingStats(
            total_videos=1,
            start_time=datetime.now()
        )

        print(f"\nProcessing: {video_path.name}")
        print(f"-" * 60)

        try:
            # Generate output path
            output_path = self.file_manager.generate_output_path(
                video_path,
                preserve_structure=True
            )

            # Ensure output directory exists
            self.file_manager.ensure_output_directory(output_path)

            # Process video
            result = self.video_processor.process_video(
                video_path=video_path,
                output_path=output_path,
                mute_padding_before_ms=self.settings.processing.mute_padding_before_ms,
                mute_padding_after_ms=self.settings.processing.mute_padding_after_ms,
                auto_download_subtitles=self.settings.opensubtitles.enabled
            )

            # Add result to statistics
            stats.add_result(result)

            # Mark as processed
            self.file_manager.mark_as_processed(
                video_path=video_path,
                success=result.success,
                segments_muted=result.segments_muted,
                error=result.error_message
            )

            # Print summary
            summary = self.video_processor.get_processing_summary(result)
            print(summary)

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            stats.failed += 1

            self.file_manager.mark_as_processed(
                video_path=video_path,
                success=False,
                error=str(e)
            )

        stats.mark_complete()
        return stats

    def get_status(self) -> dict:
        """
        Get current processing status.

        Returns:
            Dictionary with status information.
        """
        file_stats = self.file_manager.get_file_statistics()

        # Check FFmpeg availability
        ffmpeg_available, ffmpeg_version = self.video_processor.ffmpeg.check_available()

        # Validate configuration
        config_valid, config_errors = self.config_manager.validate_config()

        return {
            'config_valid': config_valid,
            'config_errors': config_errors,
            'ffmpeg_available': ffmpeg_available,
            'ffmpeg_version': ffmpeg_version,
            'total_videos': file_stats['total_videos'],
            'processed_videos': file_stats['processed_videos'],
            'unprocessed_videos': file_stats['unprocessed_videos'],
            'total_size_gb': file_stats['total_size_gb'],
            'unprocessed_size_gb': file_stats['unprocessed_size_gb'],
            'profanity_words': self.profanity_detector.get_word_count(),
            'opensubtitles_enabled': self.settings.opensubtitles.enabled,
            'max_daily_processing': self.settings.processing.max_daily_processing,
        }

    def print_status(self) -> None:
        """Print formatted status information."""
        status = self.get_status()

        print("\n" + "="*60)
        print("Cleanvid Status")
        print("="*60 + "\n")

        # Configuration
        print("Configuration:")
        if status['config_valid']:
            print("  ✓ Valid")
        else:
            print("  ✗ Invalid")
            for error in status['config_errors']:
                print(f"    - {error}")

        # FFmpeg
        print(f"\nFFmpeg:")
        if status['ffmpeg_available']:
            print(f"  ✓ Available ({status['ffmpeg_version']})")
        else:
            print(f"  ✗ Not available")

        # Files
        print(f"\nVideos:")
        print(f"  Total: {status['total_videos']}")
        print(f"  Processed: {status['processed_videos']}")
        print(f"  Unprocessed: {status['unprocessed_videos']}")
        print(f"  Total size: {status['total_size_gb']:.2f} GB")
        print(f"  Unprocessed size: {status['unprocessed_size_gb']:.2f} GB")

        # Settings
        print(f"\nSettings:")
        print(f"  Profanity words: {status['profanity_words']}")
        print(
            f"  OpenSubtitles: {'Enabled' if status['opensubtitles_enabled'] else 'Disabled'}")
        print(f"  Max daily processing: {status['max_daily_processing']}")

        print("\n" + "="*60 + "\n")

    def reset_video(self, video_path: Path) -> bool:
        """
        Reset processing status for a video.

        Args:
            video_path: Path to video file.

        Returns:
            True if video was reset, False if it wasn't processed.
        """
        return self.file_manager.reset_processed_status(video_path)

    def reset_failed_videos(self) -> int:
        """
        Reset all failed videos so they can be reprocessed.

        Returns:
            Number of failed videos that were reset.
        """
        return self.file_manager.reset_failed_videos()

    def get_failed_videos(self) -> List[Dict[str, Any]]:
        """
        Get list of videos that failed processing.

        Returns:
            List of failed video entries.
        """
        return self.file_manager.get_failed_videos()

    def get_recent_history(self, limit: int = 10) -> List[dict]:
        """
        Get recent processing history.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of recent processing log entries.
        """
        return self.file_manager.get_processing_history(limit=limit)

    def reload_config(self) -> None:
        """Reload configuration from disk."""
        self.settings = self.config_manager.reload_settings()

        # Reinitialize services with new settings
        self.file_manager = FileManager(
            path_config=self.settings.paths,
            processing_config=self.settings.processing
        )

        self.subtitle_manager = SubtitleManager(
            config=self.settings.opensubtitles
        )

        self.profanity_detector = ProfanityDetector(
            word_list_path=self.settings.get_word_list_path()
        )

        self.video_processor = VideoProcessor(
            subtitle_manager=self.subtitle_manager,
            profanity_detector=self.profanity_detector,
            ffmpeg_config=self.settings.ffmpeg
        )

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"Processor(config_dir={self.config_manager.config_dir})"

    def __str__(self) -> str:
        """String representation."""
        file_stats = self.file_manager.get_file_statistics()
        return (
            f"Processor: {file_stats['unprocessed_videos']} videos pending, "
            f"{file_stats['processed_videos']} processed"
        )
