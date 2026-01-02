"""
Scene filter management service.

Handles loading, saving, and managing custom scene skip zones for videos.
"""

import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from cleanvid.models.scene import VideoSceneFilters, SkipZone, ProcessingMode


class SceneManager:
    """
    Manages scene filters for videos.
    
    Handles CRUD operations for custom skip zones and maintains
    the scene_filters.json file.
    """
    
    def __init__(self, config_dir: Path):
        """
        Initialize SceneManager.
        
        Args:
            config_dir: Path to config directory
        """
        self.config_dir = Path(config_dir)
        self.scene_filters_path = self.config_dir / "scene_filters.json"
        self.queue_path = self.config_dir / "scene_processing_queue.json"
    
    def load_scene_filters(self) -> Dict[str, VideoSceneFilters]:
        """
        Load all scene filters from disk.
        
        Returns:
            Dictionary mapping video paths to their filters
        """
        if not self.scene_filters_path.exists():
            return {}
        
        try:
            with open(self.scene_filters_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            filters = {}
            for video_path, filter_data in data.items():
                filters[video_path] = VideoSceneFilters.from_dict(filter_data)
            
            return filters
        
        except Exception as e:
            print(f"Warning: Failed to load scene filters: {e}")
            return {}
    
    def save_scene_filters(self, filters: Dict[str, VideoSceneFilters]) -> bool:
        """
        Save scene filters to disk with automatic backup.
        
        Args:
            filters: Dictionary of video filters to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup if file exists
            if self.scene_filters_path.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = self.config_dir / f"scene_filters.json.backup.{timestamp}"
                
                try:
                    with open(self.scene_filters_path, 'r') as src:
                        with open(backup_path, 'w') as dst:
                            dst.write(src.read())
                    print(f"✓ Scene filters backup created: {backup_path.name}")
                except Exception as e:
                    print(f"Warning: Failed to create backup: {e}")
            
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict format for JSON
            data = {
                video_path: filter_obj.to_dict()
                for video_path, filter_obj in filters.items()
            }
            
            # Save to file
            with open(self.scene_filters_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
        
        except Exception as e:
            print(f"Error saving scene filters: {e}")
            return False
    
    def get_video_filters(self, video_path: str) -> Optional[VideoSceneFilters]:
        """
        Get scene filters for a specific video.
        
        Args:
            video_path: Path to video file
        
        Returns:
            VideoSceneFilters object or None if not found
        """
        filters = self.load_scene_filters()
        return filters.get(video_path)
    
    def save_video_filters(self, video_filters: VideoSceneFilters) -> None:
        """
        Save or update filters for a specific video.
        
        Args:
            video_filters: VideoSceneFilters object to save
        """
        filters = self.load_scene_filters()
        filters[video_filters.video_path] = video_filters
        self.save_scene_filters(filters)
    
    def add_skip_zone(
        self,
        video_path: str,
        title: str,
        zone: SkipZone
    ) -> VideoSceneFilters:
        """
        Add a skip zone to a video.
        
        Args:
            video_path: Path to video file
            title: Video title
            zone: SkipZone to add
        
        Returns:
            Updated VideoSceneFilters object
        """
        filters = self.load_scene_filters()
        
        if video_path in filters:
            video_filters = filters[video_path]
        else:
            video_filters = VideoSceneFilters(
                video_path=video_path,
                title=title,
                skip_zones=[]
            )
        
        video_filters.add_zone(zone)
        self.save_video_filters(video_filters)
        
        return video_filters
    
    def update_skip_zone(
        self,
        video_path: str,
        zone_id: str,
        updated_zone: SkipZone
    ) -> bool:
        """
        Update an existing skip zone.
        
        Args:
            video_path: Path to video file
            zone_id: ID of zone to update
            updated_zone: New zone data
        
        Returns:
            True if updated, False if not found
        """
        video_filters = self.get_video_filters(video_path)
        
        if not video_filters:
            return False
        
        if video_filters.update_zone(zone_id, updated_zone):
            self.save_video_filters(video_filters)
            return True
        
        return False
    
    def delete_skip_zone(self, video_path: str, zone_id: str) -> bool:
        """
        Delete a specific skip zone.
        
        Args:
            video_path: Path to video file
            zone_id: ID of zone to delete
        
        Returns:
            True if deleted, False if not found
        """
        video_filters = self.get_video_filters(video_path)
        
        if not video_filters:
            return False
        
        if video_filters.remove_zone(zone_id):
            self.save_video_filters(video_filters)
            return True
        
        return False
    
    def delete_video_filters(self, video_path: str) -> bool:
        """
        Delete all filters for a video.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if deleted, False if not found
        """
        filters = self.load_scene_filters()
        
        if video_path in filters:
            del filters[video_path]
            self.save_scene_filters(filters)
            return True
        
        return False
    
    def get_all_videos_with_filters(self) -> List[str]:
        """
        Get list of all video paths that have custom filters.
        
        Returns:
            List of video paths
        """
        filters = self.load_scene_filters()
        return list(filters.keys())
    
    def get_all_filters(self) -> Dict[str, VideoSceneFilters]:
        """
        Get all scene filters.
        
        Returns:
            Dictionary of all filters
        """
        return self.load_scene_filters()
    
    def get_filter_statistics(self) -> Dict:
        """
        Get statistics about scene filters.
        
        Returns:
            Dictionary with filter statistics
        """
        filters = self.load_scene_filters()
        
        total_videos = len(filters)
        total_zones = sum(len(f.skip_zones) for f in filters.values())
        
        # Count by mode
        mode_counts = {'skip': 0, 'blur': 0, 'black': 0}
        for video_filters in filters.values():
            for zone in video_filters.skip_zones:
                mode_counts[zone.mode.value] += 1
        
        return {
            'total_videos': total_videos,
            'total_zones': total_zones,
            'zones_by_mode': mode_counts,
            'videos_with_blur': sum(1 for f in filters.values() if any(z.mode == ProcessingMode.BLUR for z in f.skip_zones)),
            'videos_with_black': sum(1 for f in filters.values() if any(z.mode == ProcessingMode.BLACK for z in f.skip_zones)),
            'videos_with_mute': sum(1 for f in filters.values() if any(z.mute for z in f.skip_zones))
        }
    
    # Queue Management
    
    def load_queue(self) -> List[str]:
        """
        Load processing queue from disk.
        
        Returns:
            List of video paths in queue
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
    
    def save_queue(self, queue: List[str]) -> None:
        """
        Save processing queue to disk.
        
        Args:
            queue: List of video paths
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.queue_path, 'w', encoding='utf-8') as f:
                json.dump({'queue': queue}, f, indent=2)
        
        except Exception as e:
            print(f"Error saving queue: {e}")
            raise
    
    def add_to_queue(self, video_path: str) -> bool:
        """
        Add video to processing queue.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if added, False if already in queue
        """
        queue = self.load_queue()
        
        if video_path in queue:
            return False
        
        queue.append(video_path)
        self.save_queue(queue)
        return True
    
    def remove_from_queue(self, video_path: str) -> bool:
        """
        Remove video from processing queue.
        
        Args:
            video_path: Path to video file
        
        Returns:
            True if removed, False if not in queue
        """
        queue = self.load_queue()
        
        if video_path not in queue:
            return False
        
        queue.remove(video_path)
        self.save_queue(queue)
        return True
    
    def get_queue(self) -> List[str]:
        """
        Get current processing queue.
        
        Returns:
            List of video paths in queue
        """
        return self.load_queue()
    
    def clear_queue(self) -> None:
        """Clear the processing queue."""
        self.save_queue([])
    
    def __repr__(self) -> str:
        """Detailed representation."""
        filters_count = len(self.load_scene_filters())
        queue_count = len(self.load_queue())
        return (
            f"SceneManager(filters={filters_count}, "
            f"queue={queue_count}, "
            f"config_dir={self.config_dir})"
        )
    
    def __str__(self) -> str:
        """String representation."""
        filters_count = len(self.load_scene_filters())
        return f"SceneManager: {filters_count} videos with custom filters"
