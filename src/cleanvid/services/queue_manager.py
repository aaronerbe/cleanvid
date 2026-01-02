"""
Queue management for scene processing.

Handles video processing queue for batch operations with scene filters.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


class QueueManager:
    """
    Manages scene processing queue.
    
    Handles adding, removing, and processing videos in batch queue.
    """
    
    def __init__(self, config_dir: Path):
        """
        Initialize QueueManager.
        
        Args:
            config_dir: Path to config directory
        """
        self.config_dir = Path(config_dir)
        self.queue_path = self.config_dir / "scene_processing_queue.json"
    
    def load_queue(self) -> List[Dict]:
        """
        Load processing queue from disk.
        
        Returns:
            List of queue entries with video_path and metadata
        """
        if not self.queue_path.exists():
            return []
        
        try:
            with open(self.queue_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('queue', [])
        
        except Exception as e:
            print(f"Warning: Failed to load queue: {e}")
            return []
    
    def save_queue(self, queue: List[Dict]) -> bool:
        """
        Save processing queue to disk.
        
        Args:
            queue: List of queue entries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            data = {
                'queue': queue,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.queue_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
        
        except Exception as e:
            print(f"Error saving queue: {e}")
            return False
    
    def add_to_queue(self, video_path: str, priority: int = 0) -> bool:
        """
        Add video to processing queue.
        
        Args:
            video_path: Path to video file
            priority: Priority level (higher = processed first)
        
        Returns:
            True if added, False if already in queue
        """
        queue = self.load_queue()
        
        # Check if already in queue
        if any(entry['video_path'] == video_path for entry in queue):
            return False
        
        # Add to queue
        entry = {
            'video_path': video_path,
            'priority': priority,
            'added_at': datetime.now().isoformat()
        }
        
        queue.append(entry)
        
        # Sort by priority (highest first)
        queue.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return self.save_queue(queue)
    
    def remove_from_queue(self, video_path: str) -> bool:
        """
        Remove video from processing queue.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if removed, False if not in queue
        """
        queue = self.load_queue()
        
        # Filter out the video
        original_length = len(queue)
        queue = [entry for entry in queue if entry['video_path'] != video_path]
        
        if len(queue) < original_length:
            self.save_queue(queue)
            return True
        
        return False
    
    def get_queue(self) -> List[Dict]:
        """
        Get current processing queue.
        
        Returns:
            List of queue entries sorted by priority
        """
        return self.load_queue()
    
    def get_queue_size(self) -> int:
        """
        Get number of videos in queue.
        
        Returns:
            Queue size
        """
        return len(self.load_queue())
    
    def clear_queue(self) -> bool:
        """
        Clear the processing queue.
        
        Returns:
            True if successful
        """
        return self.save_queue([])
    
    def is_in_queue(self, video_path: str) -> bool:
        """
        Check if video is in queue.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if in queue, False otherwise
        """
        queue = self.load_queue()
        return any(entry['video_path'] == video_path for entry in queue)
    
    def get_next(self) -> Optional[Dict]:
        """
        Get next video from queue (highest priority).
        
        Returns:
            Queue entry dict or None if queue is empty
        """
        queue = self.load_queue()
        return queue[0] if queue else None
    
    def pop_next(self) -> Optional[Dict]:
        """
        Get and remove next video from queue.
        
        Returns:
            Queue entry dict or None if queue is empty
        """
        queue = self.load_queue()
        
        if not queue:
            return None
        
        entry = queue.pop(0)
        self.save_queue(queue)
        
        return entry
    
    def get_statistics(self) -> Dict:
        """
        Get queue statistics.
        
        Returns:
            Dictionary with queue stats
        """
        queue = self.load_queue()
        
        return {
            'total_videos': len(queue),
            'high_priority': sum(1 for e in queue if e.get('priority', 0) > 0),
            'normal_priority': sum(1 for e in queue if e.get('priority', 0) == 0),
            'oldest_entry': min((e.get('added_at') for e in queue), default=None),
            'newest_entry': max((e.get('added_at') for e in queue), default=None)
        }
    
    def __repr__(self) -> str:
        """Detailed representation."""
        size = self.get_queue_size()
        return f"QueueManager(size={size}, config_dir={self.config_dir})"
    
    def __str__(self) -> str:
        """String representation."""
        size = self.get_queue_size()
        return f"QueueManager: {size} videos queued"
