"""
Processing queue and status tracking service.

Tracks current video processing job status and steps for real-time UI updates.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime
from pathlib import Path
import json


@dataclass
class JobStep:
    """
    Single step in video processing.
    
    Attributes:
        name: Human-readable step name (e.g., "Pass 1: Apply blur filter")
        status: Current status - "pending", "running", "complete", "failed"
        started_at: When step started
        completed_at: When step completed
    """
    name: str
    status: str = "pending"  # pending, running, complete, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class ProcessingJob:
    """
    Single video processing job with steps and metadata.
    
    Attributes:
        video_path: Full path to video file
        video_name: Display name of video
        status: Overall job status - "pending", "processing", "complete", "failed"
        steps: List of processing steps
        started_at: When job started
        completed_at: When job completed
        blur_count: Number of blur filters
        black_count: Number of black filters
        skip_count: Number of skip zones
        profanity_count: Number of profanity segments
        is_batch_mode: Whether this is part of an automated batch job
    """
    video_path: str
    video_name: str
    status: str = "pending"  # pending, processing, complete, failed
    steps: List[JobStep] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Scene filter counts
    blur_count: int = 0
    black_count: int = 0
    skip_count: int = 0
    profanity_count: int = 0
    
    # Batch mode indicator
    is_batch_mode: bool = False


class ProcessingQueue:
    """
    Manages video processing queue and status tracking.
    
    Maintains current job state and persists to JSON file for
    real-time status updates via API.
    """
    
    def __init__(self, config_dir: Path):
        """
        Initialize processing queue.
        
        Args:
            config_dir: Configuration directory for storing status file
        """
        self.config_dir = config_dir
        self.status_file = config_dir / "processing_status.json"
        self.current_job: Optional[ProcessingJob] = None
        self.pending_jobs: List[ProcessingJob] = []
        
        # Ensure config dir exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing status if available
        self._load()
    
    def start_job(
        self,
        video_path: str,
        blur: int = 0,
        black: int = 0,
        skip: int = 0,
        profanity: int = 0,
        is_batch_mode: bool = False
    ) -> None:
        """
        Start a new processing job.
        
        Creates job with appropriate steps based on what processing is needed.
        
        Args:
            video_path: Full path to video file
            blur: Number of blur filters to apply
            black: Number of black filters to apply
            skip: Number of skip zones to cut
            profanity: Number of profanity segments to mute
            is_batch_mode: Whether this is part of an automated batch job
        """
        # Create new job
        job = ProcessingJob(
            video_path=video_path,
            video_name=Path(video_path).name,
            status="processing",
            started_at=datetime.now().isoformat(),
            blur_count=blur,
            black_count=black,
            skip_count=skip,
            profanity_count=profanity,
            is_batch_mode=is_batch_mode
        )
        
        # Determine processing steps based on what needs to be done
        if blur or black:
            # Pass 1: Video filters (blur/black)
            filter_types = []
            if blur:
                filter_types.append(f"{blur} blur")
            if black:
                filter_types.append(f"{black} black")
            
            step_name = f"Pass 1: Apply {', '.join(filter_types)} filter(s)"
            job.steps.append(JobStep(name=step_name, status="pending"))
        
        if skip:
            # Pass 2: Cut skip zones (or Pass 1 if no blur/black)
            pass_num = 2 if (blur or black) else 1
            step_name = f"Pass {pass_num}: Cut {skip} skip zone(s)"
            job.steps.append(JobStep(name=step_name, status="pending"))
        
        if not (blur or black or skip):
            # Profanity-only processing
            step_name = f"Mute {profanity} profanity segment(s)"
            job.steps.append(JobStep(name=step_name, status="pending"))
        
        self.current_job = job
        self._save()
    
    def update_step(self, step_index: int, status: str) -> None:
        """
        Update status of a specific step.
        
        Args:
            step_index: Index of step to update (0-based)
            status: New status - "pending", "running", "complete", "failed"
        """
        if not self.current_job:
            return
        
        if step_index < 0 or step_index >= len(self.current_job.steps):
            return
        
        step = self.current_job.steps[step_index]
        step.status = status
        
        if status == "running":
            step.started_at = datetime.now().isoformat()
        elif status in ["complete", "failed"]:
            step.completed_at = datetime.now().isoformat()
        
        self._save()
    
    def complete_job(self, success: bool = True, error: Optional[str] = None) -> None:
        """
        Mark current job as complete.
        
        Args:
            success: Whether job completed successfully
            error: Optional error message if job failed
        """
        if not self.current_job:
            return
        
        self.current_job.status = "complete" if success else "failed"
        self.current_job.completed_at = datetime.now().isoformat()
        
        # Mark any remaining steps as complete or failed
        for step in self.current_job.steps:
            if step.status == "pending" or step.status == "running":
                step.status = "complete" if success else "failed"
                if not step.completed_at:
                    step.completed_at = datetime.now().isoformat()
        
        self._save()
        
        # Clear current job - Processor will call start_job() for next video
        self.current_job = None
        self._save()
    
    def add_pending_jobs(self, video_paths: List[str]) -> None:
        """
        Add multiple videos to the pending queue.
        
        Use this for pre-loading the queue when you know all videos to process.
        
        Args:
            video_paths: List of video file paths to queue
        """
        for video_path in video_paths:
            job = ProcessingJob(
                video_path=video_path,
                video_name=Path(video_path).name,
                status="pending",
                is_batch_mode=False  # Pre-loaded queue is not batch mode
            )
            self.pending_jobs.append(job)
        
        self._save()
    
    def clear_pending_jobs(self) -> None:
        """
        Clear all pending jobs from the queue.
        """
        self.pending_jobs = []
        self._save()
    
    def get_status(self) -> dict:
        """
        Get current queue status for API.
        
        Returns:
            Dictionary with current_job, pending_count, and pending_jobs
        """
        current_job_dict = None
        if self.current_job:
            # Convert dataclass to dict
            current_job_dict = asdict(self.current_job)
        
        return {
            "current_job": current_job_dict,
            "pending_count": len(self.pending_jobs),
            "pending_jobs": [asdict(job) for job in self.pending_jobs]  # Return all jobs
        }
    
    def _save(self) -> None:
        """Save current status to JSON file."""
        try:
            status = self.get_status()
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            # Don't fail processing if status save fails
            print(f"Warning: Failed to save processing status: {e}")
    
    def _load(self) -> None:
        """Load status from JSON file if it exists."""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                
                # Restore current job if present
                if data.get('current_job'):
                    job_data = data['current_job']
                    
                    # Reconstruct JobStep objects
                    steps = [JobStep(**step) for step in job_data.get('steps', [])]
                    
                    # Reconstruct ProcessingJob
                    self.current_job = ProcessingJob(
                        video_path=job_data['video_path'],
                        video_name=job_data['video_name'],
                        status=job_data['status'],
                        steps=steps,
                        started_at=job_data.get('started_at'),
                        completed_at=job_data.get('completed_at'),
                        blur_count=job_data.get('blur_count', 0),
                        black_count=job_data.get('black_count', 0),
                        skip_count=job_data.get('skip_count', 0),
                        profanity_count=job_data.get('profanity_count', 0),
                        is_batch_mode=job_data.get('is_batch_mode', False)
                    )
                
                # Restore pending jobs if present
                if data.get('pending_jobs'):
                    self.pending_jobs = []
                    for job_data in data['pending_jobs']:
                        steps = [JobStep(**step) for step in job_data.get('steps', [])]
                        job = ProcessingJob(
                            video_path=job_data['video_path'],
                            video_name=job_data['video_name'],
                            status=job_data['status'],
                            steps=steps,
                            started_at=job_data.get('started_at'),
                            completed_at=job_data.get('completed_at'),
                            blur_count=job_data.get('blur_count', 0),
                            black_count=job_data.get('black_count', 0),
                            skip_count=job_data.get('skip_count', 0),
                            profanity_count=job_data.get('profanity_count', 0),
                            is_batch_mode=job_data.get('is_batch_mode', False)
                        )
                        self.pending_jobs.append(job)
        except Exception as e:
            # If load fails, start with clean state
            print(f"Warning: Failed to load processing status: {e}")
            self.current_job = None
            self.pending_jobs = []
