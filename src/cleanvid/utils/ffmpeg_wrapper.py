"""
FFmpeg wrapper utilities.

Provides Python interface to FFmpeg for video processing operations.
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class FFprobeResult:
    """Result from ffprobe metadata extraction."""
    path: Path
    format: str
    duration: float
    size: int
    bit_rate: int
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    frame_rate: Optional[float] = None
    audio_sample_rate: Optional[int] = None
    audio_channels: Optional[int] = None


class FFmpegWrapper:
    """
    Wrapper for FFmpeg command-line tool.
    
    Provides methods for video processing operations like muting audio,
    extracting metadata, and applying filters.
    """
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg', ffprobe_path: str = 'ffprobe'):
        """
        Initialize FFmpeg wrapper.
        
        Args:
            ffmpeg_path: Path to ffmpeg binary (default: 'ffmpeg').
            ffprobe_path: Path to ffprobe binary (default: 'ffprobe').
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
    
    def probe(self, video_path: Path) -> FFprobeResult:
        """
        Extract metadata from video file using ffprobe.
        
        Args:
            video_path: Path to video file.
        
        Returns:
            FFprobeResult with video metadata.
        
        Raises:
            FileNotFoundError: If video file not found.
            RuntimeError: If ffprobe fails.
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            return self._parse_probe_result(video_path, data)
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffprobe failed: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse ffprobe output: {e}")
    
    def _parse_probe_result(self, video_path: Path, data: Dict[str, Any]) -> FFprobeResult:
        """Parse ffprobe JSON output into FFprobeResult."""
        format_info = data.get('format', {})
        streams = data.get('streams', [])
        
        # Find video and audio streams
        video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
        audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
        
        # Extract format info
        duration = float(format_info.get('duration', 0))
        size = int(format_info.get('size', 0))
        bit_rate = int(format_info.get('bit_rate', 0))
        format_name = format_info.get('format_name', 'unknown')
        
        # Extract video info
        video_codec = video_stream.get('codec_name') if video_stream else None
        width = video_stream.get('width') if video_stream else None
        height = video_stream.get('height') if video_stream else None
        
        # Parse frame rate (can be fraction like "24000/1001")
        frame_rate = None
        if video_stream and 'r_frame_rate' in video_stream:
            try:
                num, den = map(int, video_stream['r_frame_rate'].split('/'))
                frame_rate = num / den if den != 0 else None
            except:
                frame_rate = None
        
        # Extract audio info
        audio_codec = audio_stream.get('codec_name') if audio_stream else None
        audio_sample_rate = audio_stream.get('sample_rate') if audio_stream else None
        audio_channels = audio_stream.get('channels') if audio_stream else None
        
        if audio_sample_rate:
            audio_sample_rate = int(audio_sample_rate)
        
        return FFprobeResult(
            path=video_path,
            format=format_name,
            duration=duration,
            size=size,
            bit_rate=bit_rate,
            video_codec=video_codec,
            audio_codec=audio_codec,
            width=width,
            height=height,
            frame_rate=frame_rate,
            audio_sample_rate=audio_sample_rate,
            audio_channels=audio_channels
        )
    
    def mute_audio(
        self,
        input_path: Path,
        output_path: Path,
        filter_chain: str,
        audio_codec: str = 'aac',
        audio_bitrate: str = '192k',
        threads: int = 2,
        re_encode_video: bool = False,
        video_codec: Optional[str] = None,
        video_crf: int = 23,
        progress_callback: Optional[callable] = None
    ) -> bool:
        """
        Mute audio at specific timestamps using FFmpeg volume filter.
        
        Args:
            input_path: Input video file.
            output_path: Output video file.
            filter_chain: FFmpeg audio filter chain (e.g., from create_ffmpeg_filter_chain).
            audio_codec: Audio codec to use (default: 'aac').
            audio_bitrate: Audio bitrate (default: '192k').
            threads: Number of threads to use (default: 2).
            re_encode_video: If True, re-encode video. If False, copy video stream.
            video_codec: Video codec if re-encoding (default: None).
            video_crf: Video quality if re-encoding (0-51, lower is better).
            progress_callback: Optional callback function for progress updates.
        
        Returns:
            True if successful, False otherwise.
        
        Raises:
            FileNotFoundError: If input file not found.
            RuntimeError: If FFmpeg fails.
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Input video not found: {input_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg_path,
            '-i', str(input_path),
            '-af', filter_chain,
            '-c:a', audio_codec,
            '-b:a', audio_bitrate,
            '-threads', str(threads),
        ]
        
        # Video encoding options
        if re_encode_video:
            if video_codec:
                cmd.extend(['-c:v', video_codec])
            cmd.extend(['-crf', str(video_crf)])
        else:
            cmd.extend(['-c:v', 'copy'])  # Copy video stream without re-encoding
        
        # Output file
        cmd.extend([
            '-y',  # Overwrite output file
            str(output_path)
        ])
        
        try:
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            return True
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed: {e.stderr}")
    
    def check_available(self) -> tuple[bool, str]:
        """
        Check if FFmpeg and FFprobe are available.
        
        Returns:
            Tuple of (is_available, version_string).
        """
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Extract version from first line
            version_line = result.stdout.split('\n')[0]
            return (True, version_line)
        
        except (subprocess.CalledProcessError, FileNotFoundError):
            return (False, "FFmpeg not found")
    
    def get_duration(self, video_path: Path) -> float:
        """
        Get video duration in seconds.
        
        Args:
            video_path: Path to video file.
        
        Returns:
            Duration in seconds.
        """
        probe_result = self.probe(video_path)
        return probe_result.duration
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"FFmpegWrapper(ffmpeg='{self.ffmpeg_path}', ffprobe='{self.ffprobe_path}')"
    
    def __str__(self) -> str:
        """String representation."""
        is_available, version = self.check_available()
        if is_available:
            return f"FFmpegWrapper ({version})"
        return "FFmpegWrapper (not available)"
