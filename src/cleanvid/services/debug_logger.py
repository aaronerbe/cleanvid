"""
Debug logging service for Cleanvid.

Provides centralized debug logging that can be toggled on/off via API.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from threading import Lock


class DebugLogger:
    """
    Centralized debug logger with toggle support.
    
    Logs are written to console and optionally stored in memory
    for retrieval via API.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize debug logger."""
        if self._initialized:
            return
            
        self._enabled = False
        self._log_buffer: List[Dict[str, Any]] = []
        self._max_buffer_size = 500
        self._config_path: Optional[Path] = None
        self._initialized = True
    
    def set_config_path(self, config_dir: Path) -> None:
        """Set config directory for persisting debug state."""
        self._config_path = config_dir / "debug_settings.json"
        self._load_state()
    
    def _load_state(self) -> None:
        """Load debug state from config file."""
        if self._config_path and self._config_path.exists():
            try:
                with open(self._config_path, 'r') as f:
                    data = json.load(f)
                    self._enabled = data.get('enabled', False)
            except Exception:
                pass
    
    def _save_state(self) -> None:
        """Save debug state to config file."""
        if self._config_path:
            try:
                with open(self._config_path, 'w') as f:
                    json.dump({'enabled': self._enabled}, f)
            except Exception:
                pass
    
    @property
    def enabled(self) -> bool:
        """Check if debug logging is enabled."""
        return self._enabled
    
    def enable(self) -> None:
        """Enable debug logging."""
        self._enabled = True
        self._save_state()
        self.log("DEBUG", "Debug logging ENABLED")
    
    def disable(self) -> None:
        """Disable debug logging."""
        self.log("DEBUG", "Debug logging DISABLED")
        self._enabled = False
        self._save_state()
    
    def toggle(self) -> bool:
        """Toggle debug logging. Returns new state."""
        if self._enabled:
            self.disable()
        else:
            self.enable()
        return self._enabled
    
    def log(self, category: str, message: str, data: Optional[Dict] = None) -> None:
        """
        Log a debug message.
        
        Args:
            category: Log category (e.g., "SUBTITLE", "PROFANITY", "FFMPEG")
            message: Log message
            data: Optional additional data to log
        """
        if not self._enabled:
            return
        
        timestamp = datetime.now().isoformat()
        
        # Console output
        prefix = f"[DEBUG:{category}]"
        print(f"{prefix} {message}")
        if data:
            print(f"{prefix}   Data: {json.dumps(data, default=str)[:500]}")
        
        # Buffer for API retrieval
        entry = {
            'timestamp': timestamp,
            'category': category,
            'message': message,
            'data': data
        }
        
        with self._lock:
            self._log_buffer.append(entry)
            # Trim buffer if too large
            if len(self._log_buffer) > self._max_buffer_size:
                self._log_buffer = self._log_buffer[-self._max_buffer_size:]
    
    def get_logs(self, limit: int = 100, category: Optional[str] = None) -> List[Dict]:
        """
        Get recent log entries.
        
        Args:
            limit: Max entries to return
            category: Optional filter by category
        
        Returns:
            List of log entries (newest first)
        """
        with self._lock:
            logs = list(reversed(self._log_buffer))
            
        if category:
            logs = [l for l in logs if l['category'] == category]
        
        return logs[:limit]
    
    def clear_logs(self) -> None:
        """Clear the log buffer."""
        with self._lock:
            self._log_buffer.clear()
    
    # Convenience methods for common categories
    def subtitle(self, message: str, data: Optional[Dict] = None) -> None:
        """Log subtitle-related debug info."""
        self.log("SUBTITLE", message, data)
    
    def profanity(self, message: str, data: Optional[Dict] = None) -> None:
        """Log profanity detection debug info."""
        self.log("PROFANITY", message, data)
    
    def ffmpeg(self, message: str, data: Optional[Dict] = None) -> None:
        """Log FFmpeg-related debug info."""
        self.log("FFMPEG", message, data)
    
    def queue(self, message: str, data: Optional[Dict] = None) -> None:
        """Log queue-related debug info."""
        self.log("QUEUE", message, data)
    
    def scene(self, message: str, data: Optional[Dict] = None) -> None:
        """Log scene filter debug info."""
        self.log("SCENE", message, data)
    
    def decision(self, message: str, data: Optional[Dict] = None) -> None:
        """Log processing decision debug info."""
        self.log("DECISION", message, data)
    
    def file(self, message: str, data: Optional[Dict] = None) -> None:
        """Log file operation debug info."""
        self.log("FILE", message, data)


# Global singleton instance
debug = DebugLogger()
