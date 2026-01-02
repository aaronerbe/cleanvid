"""
Scene processing service for video filtering.

Handles FFmpeg filter generation and application for blur/black modes.
"""

from typing import List, Tuple
from pathlib import Path

from cleanvid.models.scene import SkipZone, ProcessingMode


class SceneProcessor:
    """
    Processes videos with custom scene filters.
    
    Generates FFmpeg filters for blurring or blacking out video sections.
    """
    
    def __init__(self):
        """Initialize SceneProcessor."""
        pass
    
    def generate_blur_filter(self, zones: List[SkipZone]) -> str:
        """
        Generate FFmpeg boxblur filter for multiple zones.
        
        Args:
            zones: List of skip zones with blur mode
        
        Returns:
            FFmpeg filter string
        
        Example:
            boxblur=luma_radius=25:luma_power=3:enable='between(t,45.5,47.25)+between(t,60.0,65.5)'
        """
        if not zones:
            return ""
        
        # Create enable expression for all blur zones
        enable_expressions = []
        for zone in zones:
            enable_expressions.append(
                f"between(t,{zone.start_time},{zone.end_time})"
            )
        
        enable_expr = '+'.join(enable_expressions)
        
        # gblur syntax: gblur=sigma=STRENGTH:steps=STEPS:enable='EXPRESSION'
        # sigma: blur strength (0.5-100+, typically 5-20 for good privacy)
        # steps: quality of approximation (1-6, higher = better but slower)
        # Using sigma=10 for good privacy blur, steps=1 for max speed
        # gblur is MUCH faster than boxblur (single-pass vs multi-pass)
        return f"gblur=sigma=20:steps=1:enable='{enable_expr}'"
    
    def generate_black_filter(self, zones: List[SkipZone]) -> str:
        """
        Generate FFmpeg drawbox filter to black out zones.
        
        Args:
            zones: List of skip zones with black mode
        
        Returns:
            FFmpeg filter string
        
        Example:
            drawbox=x=0:y=0:w=iw:h=ih:c=black@1:t=fill:enable='between(t,45.5,47.25)+between(t,60.0,65.5)'
        """
        if not zones:
            return ""
        
        # Create enable expression for all black zones
        enable_expressions = []
        for zone in zones:
            enable_expressions.append(
                f"between(t,{zone.start_time},{zone.end_time})"
            )
        
        enable_expr = '+'.join(enable_expressions)
        
        # drawbox syntax: drawbox=x:y:width:height:color:thickness
        # x=0, y=0: top-left corner
        # w=iw, h=ih: full input width and height (covers entire frame)
        # c=black@1: black color at full opacity
        # t=fill: thickness=fill (fills the box instead of just drawing outline)
        return f"drawbox=x=0:y=0:w=iw:h=ih:c=black@1:t=fill:enable='{enable_expr}'"
    
    def generate_skip_filter(self, zones: List[SkipZone], duration: float) -> tuple[str, str]:
        """
        Generate FFmpeg trim/concat filter to cut out skip zones.
        
        This creates a filter that REMOVES the skip zones from the video,
        making the output video shorter.
        
        Args:
            zones: List of skip zones with SKIP mode
            duration: Total video duration in seconds
        
        Returns:
            Tuple of (video_filter, audio_filter) for filter_complex
        
        Example:
            Skip zones: [(100, 200), (300, 400)]
            Keep segments: [0-100, 200-300, 400-end]
            Returns filters that trim and concatenate these segments
        """
        if not zones:
            return ("", "")
        
        # Sort zones by start time
        sorted_zones = sorted(zones, key=lambda z: z.start_time)
        
        # Calculate "keep" segments (inverse of skip zones)
        keep_segments = []
        last_end = 0.0
        
        for zone in sorted_zones:
            if zone.start_time > last_end:
                # Add segment before this skip zone
                keep_segments.append((last_end, zone.start_time))
            last_end = max(last_end, zone.end_time)
        
        # Add final segment after last skip zone
        if last_end < duration:
            keep_segments.append((last_end, duration))
        
        if not keep_segments:
            # Everything is being skipped - this shouldn't happen
            return ("", "")
        
        # Build trim + concat filter
        video_parts = []
        audio_parts = []
        
        for i, (start, end) in enumerate(keep_segments, 1):
            # Video trim
            if end == duration:
                # Last segment - trim to end
                video_parts.append(f"[0:v]trim=start={start},setpts=PTS-STARTPTS[v{i}]")
                audio_parts.append(f"[0:a]atrim=start={start},asetpts=PTS-STARTPTS[a{i}]")
            else:
                # Trim with both start and end
                video_parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}]")
                audio_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]")
        
        # Build concat input list
        n = len(keep_segments)
        concat_inputs = ''.join([f"[v{i}][a{i}]" for i in range(1, n+1)])
        
        # Combine all filters
        video_filter = '; '.join(video_parts)
        audio_filter = '; '.join(audio_parts)
        concat_filter = f"{concat_inputs}concat=n={n}:v=1:a=1[outv][outa]"
        
        full_filter = f"{video_filter}; {audio_filter}; {concat_filter}"
        
        return full_filter
    
    def combine_video_filters(
        self,
        blur_zones: List[SkipZone],
        black_zones: List[SkipZone]
    ) -> str:
        """
        Combine blur and black filters into single FFmpeg filter_complex.
        
        Args:
            blur_zones: Zones to blur
            black_zones: Zones to black out
        
        Returns:
            Complete FFmpeg filter_complex string or empty if no zones
        """
        filters = []
        
        blur_filter = self.generate_blur_filter(blur_zones)
        if blur_filter:
            filters.append(blur_filter)
        
        black_filter = self.generate_black_filter(black_zones)
        if black_filter:
            filters.append(black_filter)
        
        if not filters:
            return ""
        
        # Combine filters with comma separator
        return ','.join(filters)
    
    def get_mute_segments(self, zones: List[SkipZone]) -> List[Tuple[float, float]]:
        """
        Extract mute segments from skip zones.
        
        Args:
            zones: List of skip zones
        
        Returns:
            List of (start_time, end_time) tuples for muting
        """
        mute_segments = []
        
        for zone in zones:
            if zone.mute:
                mute_segments.append((zone.start_time, zone.end_time))
        
        return mute_segments
    
    def build_ffmpeg_command(
        self,
        input_path: Path,
        output_path: Path,
        video_filter: str,
        audio_segments: List[Tuple[float, float]],
        audio_codec: str = "aac",
        audio_bitrate: str = "192k",
        video_codec: str = "copy",
        threads: int = 2
    ) -> List[str]:
        """
        Build complete FFmpeg command for scene processing.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            video_filter: FFmpeg video filter string (blur/black)
            audio_segments: List of (start, end) segments to mute
            audio_codec: Audio codec to use
            audio_bitrate: Audio bitrate
            video_codec: Video codec ('copy' to avoid re-encoding, or codec name)
            threads: Number of threads
        
        Returns:
            List of command arguments for subprocess
        """
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-threads', str(threads),
        ]
        
        # Add video filter if present
        if video_filter:
            # If using video filters, we must re-encode video
            cmd.extend([
                '-filter_complex', f'[0:v]{video_filter}[v]',
                '-map', '[v]',
            ])
        else:
            # No video filter, can copy video stream
            cmd.extend(['-map', '0:v'])
        
        # Audio handling
        # Note: Audio muting is handled separately by existing profanity muting logic
        # This just maps the audio stream
        cmd.extend([
            '-map', '0:a',
            '-c:a', audio_codec,
            '-b:a', audio_bitrate,
        ])
        
        # Video codec
        if video_filter:
            # Re-encode with H.264 when using video filters
            cmd.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '23'])
        else:
            # Copy video stream when no filters
            cmd.extend(['-c:v', video_codec])
        
        # Output file
        cmd.extend(['-y', str(output_path)])
        
        return cmd
    
    def has_video_modifications(self, zones: List[SkipZone]) -> bool:
        """
        Check if any zones require video modification (blur/black).
        
        Args:
            zones: List of skip zones
        
        Returns:
            True if blur or black zones exist
        """
        for zone in zones:
            if zone.mode in [ProcessingMode.BLUR, ProcessingMode.BLACK]:
                return True
        return False
    
    def separate_zones_by_mode(
        self,
        zones: List[SkipZone]
    ) -> Tuple[List[SkipZone], List[SkipZone], List[SkipZone]]:
        """
        Separate zones by processing mode.
        
        Args:
            zones: List of all skip zones
        
        Returns:
            Tuple of (blur_zones, black_zones, skip_zones)
        """
        blur_zones = []
        black_zones = []
        skip_zones = []
        
        for zone in zones:
            if zone.mode == ProcessingMode.BLUR:
                blur_zones.append(zone)
            elif zone.mode == ProcessingMode.BLACK:
                black_zones.append(zone)
            else:  # SKIP mode
                skip_zones.append(zone)
        
        return blur_zones, black_zones, skip_zones
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return "SceneProcessor()"
    
    def __str__(self) -> str:
        """String representation."""
        return "SceneProcessor for blur/black video filtering"
