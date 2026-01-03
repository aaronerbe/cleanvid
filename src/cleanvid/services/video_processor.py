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
        config_dir: Optional[Path] = None,
        processing_queue: Optional['ProcessingQueue'] = None
    ):
        """
        Initialize VideoProcessor.
        
        Args:
            subtitle_manager: SubtitleManager instance.
            profanity_detector: ProfanityDetector instance.
            ffmpeg_config: FFmpeg configuration.
            ffmpeg_wrapper: Optional FFmpegWrapper instance (creates default if None).
            config_dir: Optional config directory path for scene filters.
            processing_queue: Optional ProcessingQueue for status tracking.
        """
        self.subtitle_manager = subtitle_manager
        self.profanity_detector = profanity_detector
        self.ffmpeg_config = ffmpeg_config
        self.ffmpeg = ffmpeg_wrapper or FFmpegWrapper()
        self.config_dir = config_dir
        self.queue = processing_queue
    
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
            
            # Initialize scene filter counters for queue tracking
            blur_zones = []
            black_zones = []
            skip_zones = []
            
            print(f"  🔍 DEBUG: Checking for scene filters...")
            print(f"  🔍 DEBUG: config_dir = {self.config_dir}")
            
            if self.config_dir:
                print(f"  🔍 DEBUG: config_dir exists, attempting to load scene filters")
                try:
                    from cleanvid.services.scene_manager import SceneManager
                    from cleanvid.services.scene_processor import SceneProcessor
                    from cleanvid.models.scene import ProcessingMode
                    
                    scene_mgr = SceneManager(self.config_dir)
                    scene_proc = SceneProcessor()
                    
                    print(f"  🔍 DEBUG: Looking for filters for video: {str(video_path)}")
                    video_filters = scene_mgr.get_video_filters(str(video_path))
                    print(f"  🔍 DEBUG: video_filters = {video_filters}")
                    
                    if video_filters and len(video_filters.skip_zones) > 0:
                        print(f"  ✅ Found {len(video_filters.skip_zones)} scene skip zone(s)")
                        print(f"  🔍 DEBUG: Skip zones: {[{'desc': z.description, 'mode': z.mode.value, 'start': z.start_time, 'end': z.end_time} for z in video_filters.skip_zones]}")
                        
                        # Extract zones by type
                        skip_zones = video_filters.get_zones_by_mode(ProcessingMode.SKIP)
                        blur_zones = video_filters.get_zones_by_mode(ProcessingMode.BLUR)
                        black_zones = video_filters.get_zones_by_mode(ProcessingMode.BLACK)
                        scene_mute_zones = video_filters.get_mute_zones()
                        
                        print(f"  🔍 DEBUG: Skip zones: {len(skip_zones)}, Blur zones: {len(blur_zones)}, Black zones: {len(black_zones)}, Mute zones: {len(scene_mute_zones)}")
                        
                        # Generate BLUR/BLACK filters (SKIP handled later in two-pass logic)
                        if blur_zones or black_zones:
                            video_filter_complex = scene_proc.combine_video_filters(blur_zones, black_zones)
                            scene_zones_applied += len(blur_zones) + len(black_zones)
                            print(f"  ✅ Applying video filters: {len(blur_zones)} blur, {len(black_zones)} black")
                            print(f"  🔍 DEBUG: Generated filter: {video_filter_complex}")
                        
                        # Note skip zones for later two-pass processing
                        if skip_zones:
                            print(f"  ℹ️  Will CUT OUT {len(skip_zones)} skip zone(s) in second pass")
                        
                        # Extract scene mute time ranges and convert to MuteSegment objects
                        if scene_mute_zones:
                            scene_mute_ranges = scene_proc.get_mute_segments(scene_mute_zones)
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
                            print(f"  ✅ Adding {len(scene_mute_segments)} scene mute zone(s)")
                    else:
                        print(f"  ℹ️  No scene filters found for this video")
                        
                except Exception as e:
                    print(f"  ⚠️  Warning: Failed to load scene filters: {e}")
                    import traceback
                    traceback.print_exc()
                    result.add_warning(f"Scene filters not applied: {e}")
            else:
                print(f"  ℹ️  config_dir is None, skipping scene filter loading")
            
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
            
            # Count filters and start queue tracking
            blur_count = len(blur_zones)
            black_count = len(black_zones)
            skip_count = len(skip_zones)
            profanity_count = len(padded_segments)
            
            if self.queue:
                self.queue.start_job(
                    video_path=str(video_path),
                    blur=blur_count,
                    black=black_count,
                    skip=skip_count,
                    profanity=profanity_count
                )
            
            # Step 5: Process video with FFmpeg
            # Two-pass approach: BLUR/BLACK first, then SKIP cuts
            
            # Determine if we need skip processing (separate pass)
            skip_zones = []
            if self.config_dir:
                try:
                    from cleanvid.services.scene_manager import SceneManager
                    from cleanvid.models.scene import ProcessingMode
                    
                    scene_mgr = SceneManager(self.config_dir)
                    video_filters = scene_mgr.get_video_filters(str(video_path))
                    
                    if video_filters:
                        skip_zones = video_filters.get_zones_by_mode(ProcessingMode.SKIP)
                except:
                    pass
            
            # Pass 1: BLUR/BLACK + profanity muting
            if video_filter_complex:
                # If we have skip zones, use a temp output for pass 1
                if skip_zones:
                    temp_output = output_path.parent / f"{output_path.stem}_temp{output_path.suffix}"
                    print(f"  🔄 Two-pass processing: Pass 1 (BLUR/BLACK) -> temp file")
                    pass1_output = temp_output
                else:
                    pass1_output = output_path
                
                # Update queue: starting Pass 1
                if self.queue:
                    self.queue.update_step(0, "running")
                
                # Process with blur/black filters
                success = self._process_with_scene_filters(
                    input_path=video_path,
                    output_path=pass1_output,
                    video_filter_complex=video_filter_complex,
                    audio_filter_chain=audio_filter_chain,
                    padded_segments=padded_segments,
                    is_skip_mode=False
                )
                
                if not success:
                    result.mark_complete(success=False, error="Pass 1 (BLUR/BLACK) failed")
                    return result
                
                # Update queue: Pass 1 complete
                if self.queue:
                    self.queue.update_step(0, "complete" if success else "failed")
                
                # Pass 2: SKIP cuts (if needed)
                if skip_zones:
                    print(f"  🔄 Two-pass processing: Pass 2 (SKIP cuts)")
                    from cleanvid.services.scene_processor import SceneProcessor
                    
                    scene_proc = SceneProcessor()
                    
                    # Get duration of pass 1 output
                    probe_result = self.ffmpeg.probe(pass1_output)
                    duration = probe_result.duration
                    
                    # Generate skip filter
                    skip_filter = scene_proc.generate_skip_filter(skip_zones, duration)
                    
                    # Update queue: starting Pass 2
                    if self.queue:
                        self.queue.update_step(1, "running")
                    
                    # Apply skip cuts to temp file
                    success = self._process_with_scene_filters(
                        input_path=pass1_output,
                        output_path=output_path,
                        video_filter_complex=skip_filter,
                        audio_filter_chain="",  # No audio filter needed
                        padded_segments=[],
                        is_skip_mode=True
                    )
                    
                    # Clean up temp file
                    try:
                        pass1_output.unlink()
                    except:
                        pass
                    
                    if not success:
                        result.mark_complete(success=False, error="Pass 2 (SKIP) failed")
                        return result
                    
                    # Update queue: Pass 2 complete
                    if self.queue:
                        self.queue.update_step(1, "complete" if success else "failed")
                    
                    scene_zones_applied += len(skip_zones)
                    print(f"  ✅ Cut out {len(skip_zones)} scene(s) - output is shorter")
            
            # No blur/black, but we have skip zones
            elif skip_zones:
                print(f"  🔄 Single-pass processing: SKIP cuts only")
                from cleanvid.services.scene_processor import SceneProcessor
                
                scene_proc = SceneProcessor()
                
                # Get video duration
                probe_result = self.ffmpeg.probe(video_path)
                duration = probe_result.duration
                
                # Generate skip filter
                skip_filter = scene_proc.generate_skip_filter(skip_zones, duration)
                
                # Update queue: starting SKIP processing
                if self.queue:
                    self.queue.update_step(0, "running")
                
                # Apply skip cuts
                success = self._process_with_scene_filters(
                    input_path=video_path,
                    output_path=output_path,
                    video_filter_complex=skip_filter,
                    audio_filter_chain=audio_filter_chain if padded_segments else "",
                    padded_segments=padded_segments,
                    is_skip_mode=True
                )
                
                if not success:
                    result.mark_complete(success=False, error="SKIP processing failed")
                    return result
                
                # Update queue: SKIP complete
                if self.queue:
                    self.queue.update_step(0, "complete" if success else "failed")
                
                scene_zones_applied += len(skip_zones)
                print(f"  ✅ Cut out {len(skip_zones)} scene(s) - output is shorter")
            
            # No scene filters at all - standard profanity muting
            else:
                # Update queue: starting profanity muting
                if self.queue:
                    self.queue.update_step(0, "running")
                
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
                
                # Update queue: profanity muting complete
                if self.queue:
                    self.queue.update_step(0, "complete" if success else "failed")
            
            if success:
                result.output_path = output_path
                result.scene_zones_processed = scene_zones_applied
                result.has_custom_scenes = (scene_zones_applied > 0)
                result.mark_complete(success=True)
                if scene_zones_applied > 0:
                    result.add_warning(f"Applied {scene_zones_applied} scene filter(s)")
            else:
                result.mark_complete(success=False, error="FFmpeg processing failed")
            
            # Complete queue job
            if self.queue:
                self.queue.complete_job(success=result.success)
        
        except Exception as e:
            result.mark_complete(success=False, error=str(e))
            # Complete queue job on error
            if self.queue:
                self.queue.complete_job(success=False)
        
        return result
    
    def _process_with_scene_filters(
        self,
        input_path: Path,
        output_path: Path,
        video_filter_complex: str,
        audio_filter_chain: str,
        padded_segments: List[MuteSegment],
        is_skip_mode: bool = False
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
            # Using threads=0 for auto-detection (better CPU utilization)
            cmd = [
                'ffmpeg',
                '-i', str(input_path),
                '-threads', '0',  # Auto-detect optimal thread count
            ]
            
            # Handle SKIP mode vs BLUR/BLACK mode differently
            if is_skip_mode:
                # SKIP mode: filter already has [outv][outa] from trim+concat
                cmd.extend(['-filter_complex', video_filter_complex])
                cmd.extend(['-map', '[outv]', '-map', '[outa]'])
                print(f"  🔍 DEBUG: Skip mode - using [outv][outa] outputs")
            else:
                # BLUR/BLACK mode: wrap filter with [0:v]...[v]
                filter_with_labels = f"[0:v]{video_filter_complex}[v]"
                cmd.extend(['-filter_complex', filter_with_labels])
                cmd.extend(['-map', '[v]'])
                
                print(f"  🔍 DEBUG: Blur/Black mode filter: {filter_with_labels}")
                
                # Map audio with muting filter if we have segments to mute
                if padded_segments and audio_filter_chain:
                    cmd.extend(['-map', '0:a', '-af', audio_filter_chain])
                else:
                    cmd.extend(['-map', '0:a'])
            
            # Video codec settings (must re-encode when using video filters)
            # For SKIP mode (cutting), use 'fast' preset for 40% speedup
            # For BLUR/BLACK mode, keep 'medium' for better quality during visual effects
            preset = 'fast' if is_skip_mode else 'medium'
            cmd.extend(['-c:v', 'libx264', '-preset', preset, '-crf', str(self.ffmpeg_config.video_crf or 23)])
            
            # Audio codec settings
            cmd.extend(['-c:a', self.ffmpeg_config.audio_codec, '-b:a', self.ffmpeg_config.audio_bitrate])
            
            # Output file
            cmd.extend(['-y', str(output_path)])  # -y to overwrite
            
            print(f"  Running FFmpeg with scene filters...")
            print(f"  🔍 DEBUG: Full FFmpeg command:")
            print(f"  {' '.join(cmd)}")
            print(f"")
            
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
