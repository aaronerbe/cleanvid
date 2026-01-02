"""
Video processing service.

Handles video file processing including profanity detection and audio muting.
"""

import shutil
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
        ffmpeg_wrapper: Optional[FFmpegWrapper] = None,
        config_dir: Optional[Path] = None
    ):
        """
        Initialize VideoProcessor.
        
        Args:
            subtitle_manager: SubtitleManager instance.
            profanity_detector: ProfanityDetector instance.
            ffmpeg_config: FFmpeg configuration.
            ffmpeg_wrapper: Optional FFmpegWrapper instance (creates default if None).
            config_dir: Optional config directory path for scene filters.
        """
        self.subtitle_manager = subtitle_manager
        self.profanity_detector = profanity_detector
        self.ffmpeg_config = ffmpeg_config
        self.ffmpeg = ffmpeg_wrapper or FFmpegWrapper()
        self.config_dir = config_dir
    
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
            
            # Step 2.5: Load and integrate scene filters
            video_filter_complex = None
            scene_zones_applied = 0
            
            if self.config_dir:
                try:
                    from cleanvid.services.scene_manager import SceneManager
                    from cleanvid.services.scene_processor import SceneProcessor
                    from cleanvid.models.scene import ProcessingMode
                    
                    scene_mgr = SceneManager(self.config_dir)
                    scene_proc = SceneProcessor()
                    
                    video_filters = scene_mgr.get_video_filters(str(video_path))
                    
                    if video_filters and video_filters.zone_count > 0:
                        print(f"  Found {video_filters.zone_count} scene skip zone(s)")
                        
                        # Extract zones by type
                        blur_zones = video_filters.get_zones_by_mode(ProcessingMode.BLUR)
                        black_zones = video_filters.get_zones_by_mode(ProcessingMode.BLACK)
                        scene_mute_zones = video_filters.get_mute_zones()
                        
                        # Generate video filter string for blur/black effects
                        if blur_zones or black_zones:
                            video_filter_complex = scene_proc.combine_video_filters(blur_zones, black_zones)
                            scene_zones_applied += len(blur_zones) + len(black_zones)
                            print(f"  Applying video filters: {len(blur_zones)} blur, {len(black_zones)} black")
                        
                        # Extract scene mute time ranges and convert to MuteSegment objects
                        if scene_mute_zones:
                            scene_mute_ranges = scene_proc.get_mute_time_ranges(scene_mute_zones)
                            scene_mute_segments = [
                                MuteSegment(
                                    start_time=start,
                                    end_time=end,
                                    word="[scene_mute]",
                                    confidence=1.0
                                )
                                for start, end in scene_mute_ranges
                            ]
                            
                            # Merge scene mute segments with profanity segments
                            segments = segments + scene_mute_segments
                            print(f"  Adding {len(scene_mute_segments)} scene mute zone(s)")
                        
                except Exception as e:
                    print(f"  Warning: Failed to load scene filters: {e}")
                    result.add_warning(f"Scene filters not applied: {e}")
            
            if len(segments) == 0 and not video_filter_complex:
                # No profanity detected AND no scene filters - copy clean video to output
                try:
                    # Ensure output directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(video_path, output_path)
                    
                    result.output_path = output_path
                    result.status = ProcessingStatus.SKIPPED
                    result.mark_complete(success=True, error="No profanity or scene filters - clean video copied")
                    result.add_warning("Video is clean - copied to output without processing")
                    
                    print(f"  ✓ Clean video copied to output")
                    
                except Exception as copy_error:
                    result.mark_complete(success=False, error=f"Failed to copy clean video: {copy_error}")
                
                return result
            
            # Step 3: Add padding and merge overlapping segments
            padded_segments = add_padding_to_segments(
                segments,
                before_ms=mute_padding_before_ms,
                after_ms=mute_padding_after_ms
            )
            
            result.segments_muted = len(padded_segments)
            
            # Step 4: Create FFmpeg filter chain for audio muting
            audio_filter_chain = create_ffmpeg_filter_chain(padded_segments)
            
            # Step 5: Process video with FFmpeg
            # If we have video filters (blur/black), we need to use filter_complex
            if video_filter_complex:
                # Process with both video and audio filters
                success = self._process_with_scene_filters(
                    input_path=video_path,
                    output_path=output_path,
                    video_filter_complex=video_filter_complex,
                    audio_filter_chain=audio_filter_chain,
                    padded_segments=padded_segments
                )
            else:
                # Standard audio-only processing
                success = self.ffmpeg.mute_audio(
                    input_path=video_path,
                    output_path=output_path,
                    filter_chain=audio_filter_chain,
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
                if scene_zones_applied > 0:
                    result.add_warning(f"Applied {scene_zones_applied} scene filter(s)")
            else:
                result.mark_complete(success=False, error="FFmpeg processing failed")
        
        except Exception as e:
            result.mark_complete(success=False, error=str(e))
        
        return result
    
    def _process_with_scene_filters(
        self,
        input_path: Path,
        output_path: Path,
        video_filter_complex: str,
        audio_filter_chain: str,
        padded_segments: List[MuteSegment]
    ) -> bool:
        """
        Process video with both scene filters (blur/black) and audio muting.
        
        Uses FFmpeg filter_complex to apply video filters and audio muting in one pass.
        
        Args:
            input_path: Input video path.
            output_path: Output video path.
            video_filter_complex: Video filter string (e.g., "[0:v]boxblur=20:20[v]").
            audio_filter_chain: Audio filter chain for muting.
            padded_segments: Mute segments for audio.
        
        Returns:
            True if successful, False otherwise.
        """
        import subprocess
        
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build FFmpeg command with filter_complex
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-threads', str(self.ffmpeg_config.threads),
            ]
            
            # Add video filter
            cmd.extend(['-filter_complex', video_filter_complex])
            
            # Map filtered video
            cmd.extend(['-map', '[v]'])
            
            # Map audio with muting filter if we have segments to mute
            if padded_segments and audio_filter_chain:
                cmd.extend(['-map', '0:a', '-af', audio_filter_chain])
            else:
                # No audio muting needed, just copy audio
                cmd.extend(['-map', '0:a'])
            
            # Video codec settings (must re-encode when using video filters)
            cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', str(self.ffmpeg_config.video_crf or 23)])
            
            # Audio codec settings
            cmd.extend(['-c:a', self.ffmpeg_config.audio_codec, '-b:a', self.ffmpeg_config.audio_bitrate])
            
            # Output file
            cmd.extend(['-y', str(output_path)])  # -y to overwrite
            
            print(f"  Running FFmpeg with scene filters...")
            print(f"  Command: ffmpeg -i ... -filter_complex '{video_filter_complex}' ...")
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"  FFmpeg error: {result.stderr[-500:] if result.stderr else 'Unknown error'}")
                return False
            
            print(f"  ✓ Video processed with scene filters")
            return True
        
        except Exception as e:
            print(f"  Error processing with scene filters: {e}")
            return False
    
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
            if result.status == ProcessingStatus.SKIPPED:
                lines.append(f"⊘ Clean video (copied to output)")
            else:
                lines.append(f"✓ Successfully processed")
                lines.append(f"  Segments muted: {result.segments_muted}")
                lines.append(f"  Processing time: {result.duration_minutes:.1f} minutes")
            
            if result.subtitle_downloaded:
                lines.append(f"  Subtitle: Downloaded")
            
            if result.output_path:
                lines.append(f"  Output: {result.output_path}")
        
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
