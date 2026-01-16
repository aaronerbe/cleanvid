"""
Video processing service.

Handles video file processing including profanity detection and audio muting.
"""

import shutil
import os
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from cleanvid.models.processing import VideoMetadata, ProcessingResult, ProcessingStatus
from cleanvid.models.segment import MuteSegment, merge_overlapping_segments, add_padding_to_segments, create_ffmpeg_filter_chain
from cleanvid.models.config import FFmpegConfig
from cleanvid.services.subtitle_manager import SubtitleManager
from cleanvid.services.profanity_detector import ProfanityDetector
from cleanvid.services.debug_logger import debug
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
        auto_download_subtitles: bool = True,
        is_batch_mode: bool = False
    ) -> ProcessingResult:
        """
        Process a video file to mute profanity.
        
        Args:
            video_path: Path to input video file.
            output_path: Path to output video file.
            mute_padding_before_ms: Padding before detected word (milliseconds).
            mute_padding_after_ms: Padding after detected word (milliseconds).
            auto_download_subtitles: If True, downloads subtitles if missing.
            is_batch_mode: If True, marks this as part of an automated batch job.
        
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
            debug.subtitle(f"Loading subtitle for: {video_path.name}")
            subtitle_file = self.subtitle_manager.load_subtitle_file(
                video_path,
                auto_download=auto_download_subtitles
            )
            
            if subtitle_file is None:
                debug.decision(f"FAILED: No subtitle file available", {
                    'video': video_path.name,
                    'auto_download_enabled': auto_download_subtitles
                })
                result.mark_complete(
                    success=False,
                    error="No subtitle file found or could not be downloaded"
                )
                return result
            
            debug.subtitle(f"Subtitle loaded successfully", {
                'path': str(subtitle_file.path),
                'entries': len(subtitle_file.entries),
                'encoding': subtitle_file.encoding
            })
            
            result.subtitle_downloaded = auto_download_subtitles and (
                self.subtitle_manager.find_subtitle_for_video(video_path) is None
            )
            
            # Step 2: Detect profanity
            debug.profanity(f"Starting profanity detection", {
                'word_list_count': self.profanity_detector.get_word_count(),
                'subtitle_entries': len(subtitle_file.entries)
            })
            
            segments = self.profanity_detector.detect_in_subtitle_file(subtitle_file)
            
            # Always show profanity results (important info)
            print(f"  🔍 Profanity detection: {len(segments)} segment(s) found")
            if len(segments) > 0:
                unique_words = set(s.word for s in segments)
                print(f"  🔍 Words detected: {', '.join(sorted(unique_words)[:10])}{'...' if len(unique_words) > 10 else ''}")
                debug.profanity(f"Profanity found", {
                    'segment_count': len(segments),
                    'unique_words': list(unique_words)[:20]
                })
            else:
                print(f"  🔍 Word list has {self.profanity_detector.get_word_count()} words loaded")
                # Show sample of subtitle text for debugging
                if subtitle_file.entries:
                    sample_text = ' '.join([e.text for e in subtitle_file.entries[:5]])[:200]
                    print(f"  🔍 Sample subtitle text: {sample_text}...")
                debug.profanity(f"No profanity detected in subtitle", {
                    'sample_text': sample_text if subtitle_file.entries else 'N/A'
                })
            
            # Step 2.5: Load and integrate scene filters
            video_filter_complex = None
            scene_zones_applied = 0
            
            # Initialize scene filter counters for queue tracking
            blur_zones = []
            black_zones = []
            skip_zones = []
            
            debug.scene(f"Checking for scene filters", {'config_dir': str(self.config_dir)})
            
            if self.config_dir:
                try:
                    from cleanvid.services.scene_manager import SceneManager
                    from cleanvid.services.scene_processor import SceneProcessor
                    from cleanvid.models.scene import ProcessingMode
                    
                    scene_mgr = SceneManager(self.config_dir)
                    scene_proc = SceneProcessor()
                    
                    debug.scene(f"Looking for filters for video", {'video_path': str(video_path)})
                    video_filters = scene_mgr.get_video_filters(str(video_path))
                    
                    if video_filters and len(video_filters.skip_zones) > 0:
                        print(f"  ✅ Found {len(video_filters.skip_zones)} scene zone(s)")
                        debug.scene(f"Scene filters found", {
                            'zones': [{'desc': z.description, 'mode': z.mode.value, 'start': z.start_time, 'end': z.end_time} for z in video_filters.skip_zones]
                        })
                        
                        # Extract zones by type
                        skip_zones = video_filters.get_zones_by_mode(ProcessingMode.SKIP)
                        blur_zones = video_filters.get_zones_by_mode(ProcessingMode.BLUR)
                        black_zones = video_filters.get_zones_by_mode(ProcessingMode.BLACK)
                        scene_mute_zones = video_filters.get_mute_zones()
                        
                        debug.scene(f"Zones by type", {
                            'skip': len(skip_zones),
                            'blur': len(blur_zones), 
                            'black': len(black_zones),
                            'mute': len(scene_mute_zones)
                        })
                        
                        # Generate BLUR/BLACK filters (SKIP handled later in two-pass logic)
                        if blur_zones or black_zones:
                            video_filter_complex = scene_proc.combine_video_filters(blur_zones, black_zones)
                            scene_zones_applied += len(blur_zones) + len(black_zones)
                            print(f"  ✅ Applying video filters: {len(blur_zones)} blur, {len(black_zones)} black")
                            debug.scene(f"Video filter generated", {'filter': video_filter_complex})
                        
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
                        debug.scene(f"No scene filters found for this video")
                        
                except Exception as e:
                    print(f"  ⚠️  Warning: Failed to load scene filters: {e}")
                    debug.scene(f"Scene filter error", {'error': str(e)})
                    result.add_warning(f"Scene filters not applied: {e}")
            
            # DECISION POINT: Determine processing path
            if len(segments) == 0 and not video_filter_complex:
                # No profanity detected AND no scene filters - copy clean video to output
                debug.decision(f"CLEAN VIDEO - No processing needed", {
                    'video': video_path.name,
                    'profanity_segments': 0,
                    'scene_filters': False,
                    'action': 'copy_to_output'
                })
                print(f"  ℹ️  Decision: Video is CLEAN - copying to output")
                
                # Update queue status for UI
                if self.queue:
                    from cleanvid.services.processing_queue import JobStep
                    self.queue.start_job(
                        video_path=str(video_path),
                        steps=[JobStep(name="Copying clean video", status="running")],
                        blur_count=0,
                        black_count=0,
                        skip_count=0,
                        profanity_count=0
                    )
                
                try:
                    # Ensure output directory exists with proper permissions
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Fix directory permissions for NAS access
                    # Walk up and fix all parent directories we may have created
                    import os
                    current = output_path.parent
                    while str(current) != str(Path('/output')):
                        try:
                            os.chmod(current, 0o755)  # rwxr-xr-x for directories
                        except:
                            pass
                        if current.parent == current:
                            break
                        current = current.parent
                    
                    debug.file(f"Copying video to output", {
                        'source': str(video_path),
                        'dest': str(output_path)
                    })
                    
                    # Copy file
                    shutil.copy2(video_path, output_path)
                    
                    # Fix permissions for NAS access (make world-readable/writable)
                    os.chmod(output_path, 0o666)
                    debug.file(f"Permissions set to 0o666")
                    
                    # Copy SRT file (no redaction needed since no profanity was detected)
                    self._copy_srt_for_clean_video(video_path, output_path, subtitle_file)
                    
                    result.output_path = output_path
                    result.status = ProcessingStatus.SKIPPED
                    result.mark_complete(success=True, error="No profanity or scene filters - clean video copied")
                    result.add_warning("Video is clean - copied to output without processing")
                    
                    print(f"  ✓ Clean video copied to output")
                    
                    # Complete queue job
                    if self.queue:
                        self.queue.update_step(0, "complete")
                        self.queue.complete_job(success=True)
                    
                except Exception as copy_error:
                    result.mark_complete(success=False, error=f"Failed to copy clean video: {copy_error}")
                    if self.queue:
                        self.queue.update_step(0, "failed")
                        self.queue.complete_job(success=False)
                
                return result
            
            # DECISION POINT: Processing required
            debug.decision(f"PROCESSING REQUIRED", {
                'video': video_path.name,
                'profanity_segments': len(segments),
                'scene_filters': bool(video_filter_complex),
                'action': 'ffmpeg_processing'
            })
            print(f"  ℹ️  Decision: Processing required - {len(segments)} segment(s) to mute")
            
            # Step 3: Add padding and merge overlapping segments
            padded_segments = add_padding_to_segments(
                segments,
                before_ms=mute_padding_before_ms,
                after_ms=mute_padding_after_ms
            )
            
            debug.profanity(f"Segments after padding", {
                'original_count': len(segments),
                'padded_count': len(padded_segments),
                'padding_before_ms': mute_padding_before_ms,
                'padding_after_ms': mute_padding_after_ms
            })
            
            result.segments_muted = len(padded_segments)
            
            # Step 4: Create FFmpeg filter chain for audio muting
            audio_filter_chain = create_ffmpeg_filter_chain(padded_segments)
            debug.ffmpeg(f"Audio filter chain created", {'filter_length': len(audio_filter_chain) if audio_filter_chain else 0})
            
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
                    profanity=profanity_count,
                    is_batch_mode=is_batch_mode
                )
            
            # Step 5: Process video with FFmpeg
            # Strategy:
            # - If we have BLUR/BLACK: Pass 1 = blur/black + profanity, Pass 2 = skip cuts
            # - If we have SKIP only: Pass 1 = profanity muting, Pass 2 = skip cuts
            # - If no scene filters: Single pass = profanity muting only
            #
            # The key insight: profanity muting must happen BEFORE skip cuts,
            # because mute timestamps are based on original video timing.
            
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
            
            # Pass 1: BLUR/BLACK + profanity muting (or just profanity if no blur/black)
            if video_filter_complex:
                # We have blur/black filters
                if skip_zones:
                    temp_output = output_path.parent / f"{output_path.stem}_temp{output_path.suffix}"
                    print(f"  🔄 Two-pass processing: Pass 1 (BLUR/BLACK + profanity) -> temp file")
                    pass1_output = temp_output
                else:
                    pass1_output = output_path
                
                # Update queue: starting Pass 1
                if self.queue:
                    self.queue.update_step(0, "running")
                
                # Process with blur/black filters + profanity muting
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
                    
                    # Apply skip cuts to temp file (no audio filter - already muted)
                    success = self._process_with_scene_filters(
                        input_path=pass1_output,
                        output_path=output_path,
                        video_filter_complex=skip_filter,
                        audio_filter_chain="",
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
            
            # No blur/black, but we have skip zones - need two passes for correct timing
            elif skip_zones:
                print(f"  🔄 Two-pass processing: Pass 1 (profanity muting) -> temp file")
                from cleanvid.services.scene_processor import SceneProcessor
                
                scene_proc = SceneProcessor()
                
                # Pass 1: Profanity muting only
                temp_output = output_path.parent / f"{output_path.stem}_temp{output_path.suffix}"
                
                if self.queue:
                    self.queue.update_step(0, "running")
                
                if padded_segments and audio_filter_chain:
                    # Mute profanity in original video
                    success = self.ffmpeg.mute_audio(
                        input_path=video_path,
                        output_path=temp_output,
                        filter_chain=audio_filter_chain,
                        audio_codec=self.ffmpeg_config.audio_codec,
                        audio_bitrate=self.ffmpeg_config.audio_bitrate,
                        threads=self.ffmpeg_config.threads,
                        re_encode_video=self.ffmpeg_config.re_encode_video,
                        video_codec=self.ffmpeg_config.video_codec,
                        video_crf=self.ffmpeg_config.video_crf
                    )
                    print(f"  ✅ Pass 1: Muted {len(padded_segments)} profanity segment(s)")
                else:
                    # No profanity - just copy to temp
                    shutil.copy2(video_path, temp_output)
                    success = True
                    print(f"  ✅ Pass 1: No profanity detected, copied to temp")
                
                if not success:
                    result.mark_complete(success=False, error="Pass 1 (profanity muting) failed")
                    return result
                
                if self.queue:
                    self.queue.update_step(0, "complete")
                
                # Pass 2: Skip cuts
                print(f"  🔄 Two-pass processing: Pass 2 (SKIP cuts)")
                
                # Get duration of pass 1 output
                probe_result = self.ffmpeg.probe(temp_output)
                duration = probe_result.duration
                
                # Generate skip filter
                skip_filter = scene_proc.generate_skip_filter(skip_zones, duration)
                
                if self.queue:
                    self.queue.update_step(1, "running")
                
                # Apply skip cuts (no audio filter needed - already muted in pass 1)
                success = self._process_with_scene_filters(
                    input_path=temp_output,
                    output_path=output_path,
                    video_filter_complex=skip_filter,
                    audio_filter_chain="",
                    padded_segments=[],
                    is_skip_mode=True
                )
                
                # Clean up temp file
                try:
                    temp_output.unlink()
                except:
                    pass
                
                if not success:
                    result.mark_complete(success=False, error="Pass 2 (SKIP) failed")
                    return result
                
                if self.queue:
                    self.queue.update_step(1, "complete")
                
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
                
                # Step 6: Copy and adjust SRT file
                self._copy_and_adjust_srt(
                    video_path=video_path,
                    output_path=output_path,
                    subtitle_file=subtitle_file,
                    skip_zones=skip_zones if skip_zones else []
                )
                
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
        
        # Import app module to access stop flag and process tracking
        try:
            from cleanvid.web import app as web_app
            can_check_abort = True
        except:
            can_check_abort = False
        
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
                # Audio muting was already done in Pass 1, so just map outputs
                cmd.extend(['-filter_complex', video_filter_complex])
                cmd.extend(['-map', '[outv]', '-map', '[outa]'])
                print(f"  🔍 DEBUG: Skip mode - cutting scenes")
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
            
            # Run FFmpeg with Popen so we can track and kill it
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Track the process for potential abort
            if can_check_abort:
                web_app.current_ffmpeg_process = process
            
            # Wait for completion
            stdout, stderr = process.communicate()
            
            # Clear process tracking
            if can_check_abort:
                web_app.current_ffmpeg_process = None
            
            # Check if we were aborted
            if can_check_abort and web_app.stop_current_job:
                print(f"  ⛔ Processing aborted by user")
                # Clean up partial output
                try:
                    if output_path.exists():
                        output_path.unlink()
                except:
                    pass
                return False
            
            if process.returncode != 0:
                stderr_text = stderr.decode('utf-8', errors='replace') if stderr else 'Unknown error'
                print(f"  FFmpeg error: {stderr_text[-500:]}")
                return False
            
            print(f"  ✓ Video processed with scene filters")
            return True
        
        except Exception as e:
            print(f"  Error processing with scene filters: {e}")
            return False
    
    def _copy_and_adjust_srt(
        self,
        video_path: Path,
        output_path: Path,
        subtitle_file,
        skip_zones: List
    ) -> None:
        """
        Copy SRT file to output directory, redact profanity, and adjust timing if skip zones exist.
        
        Args:
            video_path: Original video path
            output_path: Output video path
            subtitle_file: SubtitleFile object from subtitle manager
            skip_zones: List of SkipZone objects that were applied
        """
        try:
            # Use the path from the already-loaded subtitle file
            srt_path = subtitle_file.path if subtitle_file else None
            
            if not srt_path or not srt_path.exists():
                print(f"  ℹ️  No SRT file found to copy")
                return
            
            # Generate output SRT path (same name as output video, .srt extension)
            output_srt = output_path.with_suffix('.srt')
            
            # Step 1: Redact profanity from subtitle file
            print(f"  📝 Redacting profanity from SRT...")
            redacted_subtitle = self._redact_profanity_in_subtitle(subtitle_file)
            
            # Step 2: If we have skip zones, adjust timing
            if skip_zones and len(skip_zones) > 0:
                print(f"  📝 Adjusting SRT timing for {len(skip_zones)} skip zone(s)...")
                
                # Save redacted SRT to temporary file first
                temp_srt = output_srt.parent / f"{output_srt.stem}_temp.srt"
                redacted_subtitle.save(temp_srt)
                
                # Import the timing adjuster
                from cleanvid.utils.srt_timing import SRTTimingAdjuster
                
                # Convert skip zones to (start, end) tuples in seconds
                skip_ranges = [(zone.start_time, zone.end_time) for zone in skip_zones]
                
                # Adjust timing and save to final output
                SRTTimingAdjuster.adjust_srt_for_skip_zones(
                    srt_path=temp_srt,
                    output_path=output_srt,
                    skip_zones=skip_ranges
                )
                
                # Clean up temp file
                try:
                    temp_srt.unlink()
                except:
                    pass
            else:
                # No skip zones - just save redacted SRT
                redacted_subtitle.save(output_srt)
                print(f"  ✓ Redacted SRT saved: {output_srt.name}")
        
        except Exception as e:
            print(f"  ⚠️  Warning: Failed to copy/adjust SRT: {e}")
            # Don't fail the entire processing job if SRT copy fails
    
    def _copy_srt_for_clean_video(
        self,
        video_path: Path,
        output_path: Path,
        subtitle_file
    ) -> None:
        """
        Copy SRT file to output directory for clean videos (no profanity detected).
        
        Since no profanity was detected, we just copy the SRT as-is.
        
        Args:
            video_path: Original video path
            output_path: Output video path
            subtitle_file: SubtitleFile object from subtitle manager
        """
        try:
            # Use the path from the already-loaded subtitle file
            srt_path = subtitle_file.path if subtitle_file else None
            
            if not srt_path or not srt_path.exists():
                print(f"  ℹ️  No SRT file found to copy")
                return
            
            # Generate output SRT path (same name as output video, .srt extension)
            output_srt = output_path.with_suffix('.srt')
            
            # Simply copy the SRT file (no redaction needed since no profanity was detected)
            shutil.copy2(srt_path, output_srt)
            
            # Fix permissions for NAS access
            import os
            os.chmod(output_srt, 0o666)
            
            print(f"  ✓ SRT copied: {output_srt.name}")
        
        except Exception as e:
            print(f"  ⚠️  Warning: Failed to copy SRT: {e}")
            # Don't fail the entire processing job if SRT copy fails
    
    def _redact_profanity_in_subtitle(self, subtitle_file):
        """
        Redact profanity in subtitle by replacing each letter with underscore.
        
        Args:
            subtitle_file: SubtitleFile object with entries
        
        Returns:
            New SubtitleFile with profanity redacted
        """
        from cleanvid.models.subtitle import SubtitleFile, SubtitleEntry
        import re
        
        # Get profanity word list from detector
        profanity_patterns = self.profanity_detector.profane_words
        
        # Create new subtitle file with redacted entries
        redacted_entries = []
        
        for entry in subtitle_file.entries:
            redacted_text = entry.text
            
            # Check each profanity pattern
            for pattern in profanity_patterns:
                # Convert wildcard pattern to regex if needed
                if '*' in pattern or '?' in pattern:
                    # Wildcard pattern
                    regex_pattern = pattern.replace('*', r'\S*').replace('?', r'\S')
                    regex = re.compile(r'\b' + regex_pattern + r'\b', re.IGNORECASE)
                    
                    # Find all matches
                    matches = regex.finditer(redacted_text)
                    for match in matches:
                        matched_word = match.group(0)
                        # Replace each letter with underscore, preserve spaces and punctuation
                        redacted_word = ''.join('_' if c.isalnum() else c for c in matched_word)
                        redacted_text = redacted_text[:match.start()] + redacted_word + redacted_text[match.end():]
                else:
                    # Exact word pattern
                    regex = re.compile(r'\b' + re.escape(pattern) + r'\b', re.IGNORECASE)
                    
                    # Find all matches and replace
                    def replace_word(match):
                        word = match.group(0)
                        # Replace each letter with underscore, preserve case structure
                        return ''.join('_' if c.isalnum() else c for c in word)
                    
                    redacted_text = regex.sub(replace_word, redacted_text)
            
            # Create new entry with redacted text
            redacted_entry = SubtitleEntry(
                index=entry.index,
                start_time=entry.start_time,
                end_time=entry.end_time,
                text=redacted_text
            )
            redacted_entries.append(redacted_entry)
        
        # Create new SubtitleFile
        return SubtitleFile(
            path=subtitle_file.path,
            entries=redacted_entries,
            encoding=subtitle_file.encoding
        )
    
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
