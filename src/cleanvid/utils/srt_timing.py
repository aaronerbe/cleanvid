"""
SRT Timing Adjuster for skip zone processing.

Adjusts subtitle timing after scenes have been cut from a video.
"""

from pathlib import Path
from typing import List, Tuple
import re


class SRTTimingAdjuster:
    """
    Adjusts SRT file timing after skip zones have been removed from video.
    
    When scenes are cut from a video, the output is shorter. Subtitles need to be:
    1. Removed if they fall entirely within a skip zone
    2. Shifted earlier if they come after a skip zone
    3. Trimmed if they partially overlap a skip zone
    """
    
    @staticmethod
    def parse_srt_time(time_str: str) -> float:
        """
        Parse SRT timestamp to seconds.
        
        Args:
            time_str: Time in format "HH:MM:SS,mmm"
        
        Returns:
            Time in seconds
        """
        # Handle both comma and period as decimal separator
        time_str = time_str.replace(',', '.')
        
        parts = time_str.split(':')
        if len(parts) != 3:
            raise ValueError(f"Invalid time format: {time_str}")
        
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
    
    @staticmethod
    def format_srt_time(seconds: float) -> str:
        """
        Format seconds to SRT timestamp.
        
        Args:
            seconds: Time in seconds
        
        Returns:
            Time in format "HH:MM:SS,mmm"
        """
        if seconds < 0:
            seconds = 0
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        # Format with comma as decimal separator (SRT standard)
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
    
    @staticmethod
    def calculate_time_offset(time: float, skip_zones: List[Tuple[float, float]]) -> float:
        """
        Calculate how much time to subtract based on skip zones before this time.
        
        Args:
            time: Original timestamp in seconds
            skip_zones: List of (start, end) tuples for skipped scenes
        
        Returns:
            Total seconds to subtract from this timestamp
        """
        offset = 0.0
        
        for start, end in skip_zones:
            if end <= time:
                # This skip zone is entirely before our time
                # Subtract the full duration
                offset += (end - start)
            elif start < time < end:
                # Our time is inside this skip zone
                # Subtract only the portion before our time
                offset += (time - start)
        
        return offset
    
    @staticmethod
    def is_inside_skip_zone(start: float, end: float, skip_zones: List[Tuple[float, float]]) -> bool:
        """
        Check if a subtitle is entirely inside a skip zone.
        
        Args:
            start: Subtitle start time
            end: Subtitle end time
            skip_zones: List of (start, end) tuples
        
        Returns:
            True if subtitle should be removed
        """
        for zone_start, zone_end in skip_zones:
            if start >= zone_start and end <= zone_end:
                return True
        return False
    
    @staticmethod
    def adjust_srt_for_skip_zones(
        srt_path: Path,
        output_path: Path,
        skip_zones: List[Tuple[float, float]]
    ) -> bool:
        """
        Adjust SRT file timing for skip zones and save to output.
        
        Args:
            srt_path: Path to input SRT file
            output_path: Path to output adjusted SRT file
            skip_zones: List of (start, end) tuples in seconds
        
        Returns:
            True if successful
        """
        if not skip_zones:
            # No skip zones - just copy the file
            import shutil
            shutil.copy2(srt_path, output_path)
            return True
        
        # Sort skip zones by start time
        sorted_zones = sorted(skip_zones, key=lambda x: x[0])
        
        try:
            # Read input SRT
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try latin-1 if UTF-8 fails
            with open(srt_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Parse SRT entries
        # SRT format:
        # 1
        # 00:00:01,000 --> 00:00:04,000
        # Subtitle text
        # (blank line)
        
        pattern = re.compile(
            r'(\d+)\s*\n'  # Index
            r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n'  # Timestamps
            r'((?:(?!\n\n|\n\d+\n\d{2}:\d{2}:\d{2}).)+)',  # Text (until blank line or next entry)
            re.DOTALL
        )
        
        matches = pattern.findall(content)
        
        adjusted_entries = []
        new_index = 1
        
        for match in matches:
            orig_index, start_str, end_str, text = match
            
            start_time = SRTTimingAdjuster.parse_srt_time(start_str)
            end_time = SRTTimingAdjuster.parse_srt_time(end_str)
            
            # Skip if entirely inside a skip zone
            if SRTTimingAdjuster.is_inside_skip_zone(start_time, end_time, sorted_zones):
                continue
            
            # Calculate time offsets
            start_offset = SRTTimingAdjuster.calculate_time_offset(start_time, sorted_zones)
            end_offset = SRTTimingAdjuster.calculate_time_offset(end_time, sorted_zones)
            
            # Adjust times
            new_start = start_time - start_offset
            new_end = end_time - end_offset
            
            # Ensure valid timing
            if new_start < 0:
                new_start = 0
            if new_end <= new_start:
                # Invalid timing after adjustment - skip this entry
                continue
            
            # Format new entry
            adjusted_entries.append({
                'index': new_index,
                'start': SRTTimingAdjuster.format_srt_time(new_start),
                'end': SRTTimingAdjuster.format_srt_time(new_end),
                'text': text.strip()
            })
            new_index += 1
        
        # Write output SRT
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in adjusted_entries:
                f.write(f"{entry['index']}\n")
                f.write(f"{entry['start']} --> {entry['end']}\n")
                f.write(f"{entry['text']}\n\n")
        
        print(f"  ✓ Adjusted SRT: {len(matches)} entries → {len(adjusted_entries)} entries")
        
        return True
