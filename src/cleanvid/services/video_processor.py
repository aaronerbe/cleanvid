"""
Video processing service.

Handles video file processing including profanity detection and audio muting.
"""

from pathlib import Path
from typing import Optional, List
from datetime import datetime

from cleanvid.models.processing import VideoMetadata, ProcessingResult, ProcessingStatus
from cleanvid.models.segment import MuteSegment, merge_overlapping_segments, add_padding_to_segments, create_ffmpeg_filter_chain
from cleanvid.models.config import FFmpegConfig
from cleanvid.services.subtitle_manager import SubtitleManager
from cleanvid.services.profanity_detector import ProfanityDetector
from cleanvid.utils.ffmpeg_wrapper import FFmpegWrapper, FFprobeResult


class VideoProcessor:
    """
    Processes video files to mute profanity.
    
    Orchestrates subtitle loading, profanity detection, and video processing
    using FFmpeg to create filtered output videos.
    """
    
    def __init__(
        self,
        subtitle_manager: SubtitleManager,
        profanity_detector: ProfanityDetector,
        ffmpeg_config: FFmpegConfig,
        ffmpeg_wrapper: Optional[FFmpegWrapper] = None
    ):
        """
        Initialize VideoProcessor.
        
        Args:
            subtitle_manager: SubtitleManager instance.
            profanity_detector: ProfanityDetector instance.
            ffmpeg_config: FFmpeg configuration.
            ffmpeg_wrapper: Optional FFmpegWrapper instance (creates default if None).
        """
        self.subtitle_manager = subtitle_manager
        self.profanity_detector = profanity_detector
        self.ffmpeg_config = ffmpeg_config
        self.ffmpeg = ffmpeg_wrapper or FFmpegWrapper()
    
    def extract_metadata(self, video_path: Path) -> VideoMetadata:
        """
        Extract metadata from video file.
        
        Args:
            video_path: Path to video file.
        
        Returns:
            VideoMetadata object.
        
        Raises:
            FileNotFoundError: If video file not found.
            RuntimeError: If metadata extraction fails.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Get file size
        size_bytes = video_path.stat().st_size
        
        # Probe with ffmpeg
        probe_result = self.ffmpeg.probe(video_path)
        
        # Check for subtitle
        subtitle_path = self.subtitle_manager.find_subtitle_for_video(video_path)
        
        return VideoMetadata(
            path=video_path,
            size_bytes=size_bytes,
            duration_seconds=probe_result.duration,
            width=probe_result.width or 0,
            height=probe_result.height or 0,
            video_codec=probe_result.video_codec or 'unknown',
            audio_codec=probe_result.audio_codec or 'unknown',
            has_subtitles=(subtitle_path is not None),
            subtitle_path=subtitle_path
        )
    
    def process_video(
        self,
        video_path: Path,
        output_path: Path,
        mute_padding_before_ms: int = 500,
        mute_padding_after_ms: int = 500,
        auto_download_subtitles: bool = True
    ) -> ProcessingResult:
        """
        Process a video file to mute profanity.
        
        Args:
            video_path: Path to input video file.
            output_path: Path to output video file.
            mute_padding_before_ms: Padding before detected word (milliseconds).
            mute_padding_after_ms: Padding after detected word (milliseconds).
            auto_download_subtitles: If True, downloads subtitles if missing.
        
        Returns:
            ProcessingResult with processing details.
        """
        start_time = datetime.now()
        
        result = ProcessingResult(
            video_path=video_path,
            status=ProcessingStatus.PROCESSING,
            start_time=start_time
        )
        
        try:
            # Step 1: Load subtitle file
            subtitle_file = self.subtitle_manager.load_subtitle_file(
                video_path,
                auto_download=auto_download_subtitles
            )
            
            if subtitle_file is None:
                result.mark_complete(
                    success=False,
                    error="No subtitle file found or could not be downloaded"
                )
                return result
            
            result.subtitle_downloaded = auto_download_subtitles and (
                self.subtitle_manager.find_subtitle_for_video(video_path) is None
            )
            
            # Step 2: Detect profanity
            segments = self.profanity_detector.detect_in_subtitle_file(subtitle_file)
            
            if len(segments) == 0:
                # No profanity detected - video is clean
                result.status = ProcessingStatus.SKIPPED
                result.mark_complete(success=True, error="No profanity detected")
                result.add_warning("Video is clean - no processing needed")
                return result
            
            # Step 3: Add padding and merge overlapping segments
            padded_segments = add_padding_to_segments(
                segments,
                before_ms=mute_padding_before_ms,
                after_ms=mute_padding_after_ms
            )
            
            result.segments_muted = len(padded_segments)
            
            # Step 4: Create FFmpeg filter chain
            filter_chain = create_ffmpeg_filter_chain(padded_segments)
            
            # Step 5: Process video with FFmpeg
            success = self.ffmpeg.mute_audio(
                input_path=video_path,
                output_path=output_path,
                filter_chain=filter_chain,
                audio_codec=self.ffmpeg_config.audio_codec,
                audio_bitrate=self.ffmpeg_config.audio_bitrate,
                threads=self.ffmpeg_config.threads,
                re_encode_video=self.ffmpeg_config.re_encode_video,
                video_codec=self.ffmpeg_config.video_codec,
                video_crf=self.ffmpeg_config.video_crf
            )
            
            if success:
                result.output_path = output_path
                result.mark_complete(success=True)
            else:
                result.mark_complete(success=False, error="FFmpeg processing failed")
        
        except Exception as e:
            result.mark_complete(success=False, error=str(e))
        
        return result
    
    def can_process(self, video_path: Path) -> tuple[bool, Optional[str]]:
        """
        Check if a video can be processed.
        
        Args:
            video_path: Path to video file.
        
        Returns:
            Tuple of (can_process, reason_if_not).
        """
        # Check file exists
        if not video_path.exists():
            return (False, "Video file not found")
        
        # Check FFmpeg available
        ffmpeg_available, _ = self.ffmpeg.check_available()
        if not ffmpeg_available:
            return (False, "FFmpeg not available")
        
        # Check can get metadata
        try:
            metadata = self.extract_metadata(video_path)
        except Exception as e:
            return (False, f"Failed to extract metadata: {e}")
        
        # Check has video stream
        if metadata.width == 0 or metadata.height == 0:
            return (False, "No video stream found")
        
        # Check duration
        if metadata.duration_seconds <= 0:
            return (False, "Invalid duration")
        
        return (True, None)
    
    def estimate_processing_time(self, video_path: Path) -> float:
        """
        Estimate processing time for a video.
        
        Args:
            video_path: Path to video file.
        
        Returns:
            Estimated time in seconds.
        """
        try:
            metadata = self.extract_metadata(video_path)
            
            # Base estimate: ~1-2x real-time for copy mode
            # ~5-10x real-time for re-encode mode
            if self.ffmpeg_config.re_encode_video:
                multiplier = 7.5  # Average of 5-10x
            else:
                multiplier = 1.5  # Average of 1-2x
            
            # 4K videos take longer
            if metadata.is_4k:
                multiplier *= 1.5
            
            return metadata.duration_seconds * multiplier
        
        except Exception:
            # Fallback estimate
            return 600.0  # 10 minutes
    
    def get_processing_summary(self, result: ProcessingResult) -> str:
        """
        Get human-readable processing summary.
        
        Args:
            result: ProcessingResult to summarize.
        
        Returns:
            Formatted summary string.
        """
        lines = [
            f"Video: {result.video_path.name}",
            f"Status: {result.status.value}",
        ]
        
        if result.success:
            lines.append(f"✓ Successfully processed")
            lines.append(f"  Segments muted: {result.segments_muted}")
            lines.append(f"  Processing time: {result.duration_minutes:.1f} minutes")
            
            if result.subtitle_downloaded:
                lines.append(f"  Subtitle: Downloaded")
            
            if result.output_path:
                lines.append(f"  Output: {result.output_path}")
        
        elif result.status == ProcessingStatus.SKIPPED:
            lines.append(f"⊘ Skipped (no profanity detected)")
        
        else:
            lines.append(f"✗ Failed")
            if result.error_message:
                lines.append(f"  Error: {result.error_message}")
        
        if result.warnings:
            for warning in result.warnings:
                lines.append(f"  Warning: {warning}")
        
        return "\n".join(lines)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"VideoProcessor(ffmpeg_available={self.ffmpeg.check_available()[0]}, "
            f"re_encode={self.ffmpeg_config.re_encode_video})"
        )
    
    def __str__(self) -> str:
        """String representation."""
        ffmpeg_available, version = self.ffmpeg.check_available()
        status = "ready" if ffmpeg_available else "FFmpeg not available"
        return f"VideoProcessor ({status})"
