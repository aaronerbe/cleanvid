"""
Web dashboard Flask application for Cleanvid.

Provides REST API and web interface for monitoring video processing.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any
import threading
import time

from cleanvid.services.processor import Processor
from cleanvid.services.config_manager import ConfigManager


app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize processor
processor = None

# Background worker control
worker_thread = None
worker_running = False
stop_current_job = False  # Signal to abort current processing
current_ffmpeg_process = None  # Track current FFmpeg subprocess for killing


def get_processor():
    """Get or create processor instance."""
    global processor
    if processor is None:
        processor = Processor()
    return processor


def background_queue_worker():
    """Background worker that processes pending queue jobs."""
    global worker_running, stop_current_job
    
    print("🔄 Background queue worker started")
    
    while worker_running:
        try:
            proc = get_processor()
            
            # Check if there are pending jobs and no current job
            if hasattr(proc, 'processing_queue') and proc.processing_queue:
                queue_status = proc.processing_queue.get_status()
                
                # If no current job but pending jobs exist, process next one
                if not queue_status['current_job'] and queue_status['pending_count'] > 0:
                    # Reset abort flag before starting new job
                    stop_current_job = False
                    
                    # Get next pending job
                    next_job = proc.processing_queue.pending_jobs[0]
                    video_path = Path(next_job.video_path)
                    job_type = getattr(next_job, 'job_type', 'process')  # Default to 'process' for backwards compat
                    
                    print(f"\n📹 Processing queued video: {video_path.name} (type: {job_type})")
                    
                    # Remove from pending
                    proc.processing_queue.pending_jobs.pop(0)
                    proc.processing_queue._save()
                    
                    if job_type == "bypass":
                        # BYPASS: Copy without processing
                        print(f"  ➡️  Bypassing - copying to output without filters")
                        
                        from cleanvid.services.processing_queue import ProcessingJob, JobStep
                        job = ProcessingJob(
                            video_path=str(video_path),
                            video_name=video_path.name,
                            status="processing",
                            started_at=datetime.now().isoformat(),
                            steps=[JobStep(name="Copying video to output", status="running")],
                            job_type="bypass"
                        )
                        proc.processing_queue.current_job = job
                        proc.processing_queue._save()
                        
                        success = proc.bypass_video(video_path)
                        
                        job.steps[0].status = "complete" if success else "failed"
                        job.status = "complete" if success else "failed"
                        job.completed_at = datetime.now().isoformat()
                        proc.processing_queue._save()
                        
                        proc.processing_queue.current_job = None
                        proc.processing_queue._save()
                        
                        print(f"✅ Bypassed: {video_path.name}")
                    else:
                        # PROCESS: Normal flow (detects profanity, applies scene filters)
                        print(f"  ⚙️  Processing - will detect profanity and apply any scene filters")
                        
                        output_path = proc.file_manager.generate_output_path(
                            video_path,
                            preserve_structure=True
                        )
                        
                        proc.file_manager.ensure_output_directory(output_path)
                        
                        result = proc.video_processor.process_video(
                            video_path=video_path,
                            output_path=output_path,
                            mute_padding_before_ms=proc.settings.processing.mute_padding_before_ms,
                            mute_padding_after_ms=proc.settings.processing.mute_padding_after_ms,
                            auto_download_subtitles=proc.settings.opensubtitles.enabled,
                            is_batch_mode=False
                        )
                        
                        proc.file_manager.mark_as_processed(
                            video_path=video_path,
                            success=result.success,
                            segments_muted=result.segments_muted,
                            error=result.error_message
                        )
                        
                        print(f"✅ Completed: {video_path.name}")
            
        except Exception as e:
            print(f"❌ Queue worker error: {e}")
            import traceback
            traceback.print_exc()
            # Clear current job on error to prevent stuck queue
            try:
                proc = get_processor()
                if hasattr(proc, 'processing_queue') and proc.processing_queue:
                    proc.processing_queue.complete_job(success=False)
            except:
                pass
        
        # Sleep for 2 seconds before checking again
        time.sleep(2)
    
    print("🛑 Background queue worker stopped")


def start_queue_worker():
    """Start the background queue worker thread."""
    global worker_thread, worker_running
    
    if worker_thread is None or not worker_thread.is_alive():
        worker_running = True
        worker_thread = threading.Thread(target=background_queue_worker, daemon=True)
        worker_thread.start()
        print("✅ Queue worker thread started")


def stop_queue_worker():
    """Stop the background queue worker thread."""
    global worker_running
    worker_running = False
    print("⏹️  Queue worker stopping...")


@app.route('/')
def index():
    """Serve the dashboard HTML."""
    return send_from_directory('static', 'dashboard.html')


@app.route('/queue.html')
def queue_page():
    """Serve the queue HTML."""
    return send_from_directory('static', 'queue.html')


@app.route('/failed.html')
def failed_page():
    """Serve the failed videos HTML."""
    return send_from_directory('static', 'failed.html')


@app.route('/browse.html')
def browse_page():
    """Serve the browse & process HTML."""
    return send_from_directory('static', 'browse.html')


@app.route('/help.html')
def help_page():
    """Serve the help & documentation HTML."""
    return send_from_directory('static', 'help.html')


@app.route('/compare.html')
def compare_page():
    """Serve the video comparison HTML."""
    return send_from_directory('static', 'compare.html')


@app.route('/unprocessed.html')
def unprocessed_page():
    """Serve the unprocessed videos HTML."""
    return send_from_directory('static', 'unprocessed.html')


@app.route('/api/status')
def api_status():
    """Get current system status."""
    try:
        proc = get_processor()
        status = proc.get_status()
        
        # Add additional info
        status['timestamp'] = datetime.now().isoformat()
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history')
def api_history():
    """Get processing history."""
    try:
        proc = get_processor()
        limit = request.args.get('limit', 20, type=int)
        history = proc.get_recent_history(limit=limit)
        
        return jsonify({
            'history': history,
            'total': len(history)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/failures')
def api_failures():
    """Get failed videos only."""
    try:
        proc = get_processor()
        
        # Get failed videos directly from file manager (gets ALL failed, not just recent 100)
        failures = proc.get_failed_videos()
        
        # Group by error type (dynamically extracted from actual error messages)
        error_groups = {}
        for failure in failures:
            error = failure.get('error', 'Unknown error')
            error_type = extract_error_type(error)
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(failure)
        
        return jsonify({
            'failures': failures,
            'total': len(failures),
            'error_groups': error_groups
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/unprocessed')
def api_unprocessed():
    """Get unprocessed videos (input videos without corresponding output)."""
    try:
        proc = get_processor()
        
        # Get unprocessed videos
        unprocessed = proc.file_manager.get_unprocessed_videos()
        
        # Build response with video info
        videos = []
        for video_path in unprocessed:
            try:
                size_bytes = video_path.stat().st_size if video_path.exists() else 0
                videos.append({
                    'path': str(video_path),
                    'name': video_path.name,
                    'size_mb': size_bytes / (1024 * 1024)
                })
            except:
                videos.append({
                    'path': str(video_path),
                    'name': video_path.name,
                    'size_mb': 0
                })
        
        # Sort by path for consistent ordering
        videos.sort(key=lambda v: v['path'])
        
        return jsonify({
            'videos': videos,
            'total': len(videos)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/statistics')
def api_statistics():
    """Get processing statistics."""
    try:
        proc = get_processor()
        file_stats = proc.file_manager.get_file_statistics()
        
        # Calculate success rate from history
        history = proc.get_recent_history(limit=100)
        total_processed = len(history)
        successful = sum(1 for h in history if h.get('success', False))
        success_rate = (successful / total_processed * 100) if total_processed > 0 else 0
        
        return jsonify({
            'file_stats': file_stats,
            'processing_stats': {
                'total_processed': total_processed,
                'successful': successful,
                'failed': total_processed - successful,
                'success_rate': round(success_rate, 1)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/processing-status')
def api_processing_status():
    """Get current processing/task status."""
    try:
        proc = get_processor()
        recent_history = proc.get_recent_history(limit=1)
        
        # Check if last processing was within last 90 seconds (more accurate)
        if recent_history:
            last_entry = recent_history[0]
            last_time = datetime.fromisoformat(last_entry['timestamp'])
            time_diff = (datetime.now() - last_time).total_seconds()
            
            is_processing = time_diff < 90  # 90 seconds - more accurate than 5 minutes
            last_processed = recent_history[0]
        else:
            is_processing = False
            last_processed = None
        
        return jsonify({
            'is_processing': is_processing,
            'last_processed': last_processed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def api_process():
    """Add a specific video to the processing queue."""
    try:
        data = request.json
        video_path = data.get('video_path')
        
        if not video_path:
            return jsonify({'error': 'video_path required'}), 400
        
        proc = get_processor()
        video_path = Path(video_path)
        
        # Check if exists
        if not video_path.exists():
            return jsonify({'error': f'Video not found: {video_path}'}), 404
        
        # Add to queue
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            proc.processing_queue.add_pending_jobs([str(video_path)])
            
            return jsonify({
                'success': True,
                'queued': 1,
                'message': f'Added {video_path.name} to processing queue. Processing will begin shortly.'
            })
        else:
            return jsonify({'error': 'Processing queue not available'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-all', methods=['POST'])
def api_process_all():
    """Add all unprocessed videos to the processing queue."""
    try:
        proc = get_processor()
        
        # Get all unprocessed videos
        unprocessed_videos = proc.file_manager.get_unprocessed_videos()
        
        if len(unprocessed_videos) == 0:
            return jsonify({
                'success': True,
                'queued': 0,
                'message': 'No unprocessed videos found'
            })
        
        # Add all to queue
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            video_paths = [str(v) for v in unprocessed_videos]
            proc.processing_queue.add_pending_jobs(video_paths)
            
            return jsonify({
                'success': True,
                'queued': len(video_paths),
                'message': f'Added {len(video_paths)} video(s) to processing queue. Processing will begin shortly.'
            })
        else:
            return jsonify({'error': 'Processing queue not available'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/process-multiple', methods=['POST'])
def api_process_multiple():
    """Add multiple selected videos to the processing queue."""
    try:
        data = request.json
        video_paths = data.get('video_paths', [])
        
        if not video_paths:
            return jsonify({'error': 'video_paths required'}), 400
        
        proc = get_processor()
        
        # Add to queue
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            proc.processing_queue.add_pending_jobs(video_paths)
            
            return jsonify({
                'success': True,
                'queued': len(video_paths),
                'message': f'Added {len(video_paths)} video(s) to processing queue.'
            })
        else:
            return jsonify({'error': 'Processing queue not available'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/process-folder', methods=['POST'])
def api_process_folder():
    """Add all videos in a folder (recursively) to the processing queue."""
    try:
        data = request.json
        folder_path = data.get('folder_path')
        
        if not folder_path:
            return jsonify({'error': 'folder_path required'}), 400
        
        proc = get_processor()
        folder_path = Path(folder_path)
        
        # Security: ensure path is within input directory
        input_dir = proc.file_manager.path_config.input_dir
        try:
            folder_path.relative_to(input_dir)
        except ValueError:
            return jsonify({'error': 'Access denied - folder outside input directory'}), 403
        
        if not folder_path.exists():
            return jsonify({'error': f'Folder not found: {folder_path}'}), 404
        
        if not folder_path.is_dir():
            return jsonify({'error': f'Path is not a folder: {folder_path}'}), 400
        
        # Find all video files recursively
        video_extensions = proc.file_manager.processing_config.video_extensions
        videos_found = []
        
        for ext in video_extensions:
            videos_found.extend(folder_path.rglob(f'*{ext}'))
        
        # Filter out Synology metadata
        videos_found = [
            v for v in videos_found 
            if not proc.file_manager._is_synology_metadata_path(v)
        ]
        
        if len(videos_found) == 0:
            return jsonify({
                'success': True,
                'queued': 0,
                'message': 'No video files found in folder'
            })
        
        # Add to queue
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            video_paths = [str(v) for v in videos_found]
            proc.processing_queue.add_pending_jobs(video_paths)
            
            return jsonify({
                'success': True,
                'queued': len(video_paths),
                'message': f'Added {len(video_paths)} video(s) from folder to queue.'
            })
        else:
            return jsonify({'error': 'Processing queue not available'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset a video's processing status."""
    try:
        data = request.json
        video_path = data.get('video_path')
        
        if not video_path:
            return jsonify({'error': 'video_path required'}), 400
        
        proc = get_processor()
        video_path = Path(video_path)
        
        success = proc.reset_video(video_path)
        
        return jsonify({
            'success': success,
            'message': 'Video reset successfully' if success else 'Video was not processed'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset-failed', methods=['POST'])
def api_reset_failed():
    """Reset all failed videos."""
    try:
        proc = get_processor()
        count = proc.reset_failed_videos()
        
        return jsonify({
            'success': True,
            'count': count,
            'message': f'Reset {count} failed video(s)'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bypass', methods=['POST'])
def api_bypass():
    """Bypass a video by copying directly to output."""
    try:
        data = request.json
        video_path = data.get('video_path')
        
        if not video_path:
            return jsonify({'error': 'video_path required'}), 400
        
        proc = get_processor()
        video_path = Path(video_path)
        
        success = proc.bypass_video(video_path)
        
        return jsonify({
            'success': success,
            'message': 'Video bypassed successfully' if success else 'Bypass failed'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bypass-multiple', methods=['POST'])
def api_bypass_multiple():
    """Add multiple videos to bypass queue for background processing."""
    try:
        data = request.json
        video_paths = data.get('video_paths', [])
        
        if not video_paths:
            return jsonify({'error': 'video_paths required'}), 400
        
        proc = get_processor()
        
        # Add all videos to the pending queue as BYPASS jobs
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            from cleanvid.services.processing_queue import ProcessingJob
            from pathlib import Path
            
            for video_path in video_paths:
                job = ProcessingJob(
                    video_path=video_path,
                    video_name=Path(video_path).name,
                    status="pending",
                    is_batch_mode=False,
                    job_type="bypass"  # Mark as bypass job
                )
                proc.processing_queue.pending_jobs.append(job)
            
            proc.processing_queue._save()
            
            return jsonify({
                'success': True,
                'queued': len(video_paths),
                'message': f'Added {len(video_paths)} video(s) to bypass queue. Processing will begin shortly.'
            })
        else:
            return jsonify({'error': 'Processing queue not available'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search')
def api_search():
    """Search for videos by name."""
    try:
        query = request.args.get('q', '').lower()
        
        if not query:
            return jsonify({'error': 'Query parameter "q" required'}), 400
        
        proc = get_processor()
        all_videos = proc.file_manager.discover_videos()
        
        # Filter by query
        matches = [
            str(video) for video in all_videos
            if query in video.name.lower()
        ]
        
        return jsonify({
            'matches': matches[:20],  # Limit to 20 results
            'total': len(matches)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/queue')
def api_get_queue():
    """Get processing queue status."""
    try:
        proc = get_processor()
        
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            status = proc.processing_queue.get_status()
            return jsonify(status)
        else:
            return jsonify({
                'current_job': None,
                'pending_count': 0,
                'pending_jobs': []
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/queue/<int:job_index>', methods=['DELETE'])
def api_delete_queue_job(job_index):
    """Delete a job from the pending queue."""
    try:
        proc = get_processor()
        
        if not hasattr(proc, 'processing_queue') or not proc.processing_queue:
            return jsonify({'error': 'Queue not available'}), 404
        
        # Check if job_index is valid
        if job_index < 0 or job_index >= len(proc.processing_queue.pending_jobs):
            return jsonify({'error': 'Invalid job index'}), 404
        
        # Remove the job
        removed_job = proc.processing_queue.pending_jobs.pop(job_index)
        proc.processing_queue._save()
        
        return jsonify({
            'success': True,
            'message': f'Removed {removed_job.video_name} from queue'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/queue/stop', methods=['POST'])
def api_stop_queue():
    """Stop the queue worker (pause processing after current job)."""
    global worker_running
    
    try:
        if not worker_running:
            return jsonify({
                'success': False,
                'message': 'Queue is already stopped'
            })
        
        worker_running = False
        
        return jsonify({
            'success': True,
            'message': 'Queue paused. Current job will finish, then processing will stop.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/queue/abort', methods=['POST'])
def api_abort_current():
    """Abort the current job immediately and stop the queue."""
    global worker_running, stop_current_job, current_ffmpeg_process
    
    try:
        # Set flags to stop
        worker_running = False
        stop_current_job = True
        
        # Kill FFmpeg process if running
        if current_ffmpeg_process is not None:
            try:
                current_ffmpeg_process.terminate()
                print("⛔ Terminated FFmpeg process")
            except:
                pass
        
        # Clear current job from queue
        proc = get_processor()
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            current_job = proc.processing_queue.current_job
            if current_job:
                video_name = current_job.video_name
                proc.processing_queue.current_job = None
                proc.processing_queue._save()
                
                # Clean up any temp files
                try:
                    import glob
                    output_dir = proc.file_manager.path_config.output_dir
                    temp_files = glob.glob(str(output_dir / '**/*_temp.*'), recursive=True)
                    for temp_file in temp_files:
                        Path(temp_file).unlink()
                        print(f"🗑️  Cleaned up temp file: {temp_file}")
                except:
                    pass
                
                return jsonify({
                    'success': True,
                    'message': f'Aborted processing of {video_name}. Queue stopped.'
                })
        
        return jsonify({
            'success': True,
            'message': 'Queue stopped (no active job to abort)'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/queue/resume', methods=['POST'])
def api_resume_queue():
    """Resume the queue worker (start processing)."""
    global worker_running, worker_thread, stop_current_job
    
    try:
        if worker_running:
            return jsonify({
                'success': False,
                'message': 'Queue is already running'
            })
        
        # Reset stop flag
        stop_current_job = False
        
        # Check for stuck jobs before resuming
        proc = get_processor()
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            queue_status = proc.processing_queue.get_status()
            
            # If there's a current job, it might be stuck - clear it
            if queue_status.get('current_job'):
                print("⚠️  Warning: Found stuck job on resume, clearing it")
                proc.processing_queue.current_job = None
                proc.processing_queue._save()
        
        # Restart the worker
        start_queue_worker()
        
        return jsonify({
            'success': True,
            'message': 'Queue processing resumed (cleared any stuck jobs)'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/queue/status')
def api_queue_worker_status():
    """Get queue worker status (running/stopped)."""
    global worker_running
    
    return jsonify({
        'worker_running': worker_running,
        'status': 'running' if worker_running else 'stopped'
    })


@app.route('/api/queue/force-reset', methods=['POST'])
def api_force_reset_queue():
    """Force reset queue - clears stuck job and restarts worker."""
    global worker_running
    
    try:
        # Stop worker if running
        was_running = worker_running
        worker_running = False
        
        # Wait a moment for worker to stop
        import time
        time.sleep(1)
        
        # Clear any stuck current job
        proc = get_processor()
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            if proc.processing_queue.current_job:
                print("⚠️  Force reset: Clearing stuck job")
                proc.processing_queue.current_job = None
                proc.processing_queue._save()
        
        # Restart worker if it was running
        if was_running:
            start_queue_worker()
            return jsonify({
                'success': True,
                'message': 'Queue force reset complete - worker restarted'
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Queue force reset complete - worker remains stopped'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/processing/status')
def api_get_processing_status():
    """Get current processing queue status."""
    try:
        proc = get_processor()
        
        # Get queue status from processing queue
        if hasattr(proc, 'processing_queue') and proc.processing_queue:
            status = proc.processing_queue.get_status()
            return jsonify(status)
        else:
            # No queue available - return empty status
            return jsonify({
                'current_job': None,
                'pending_count': 0,
                'pending_jobs': []
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/browse')
def api_browse():
    """Browse filesystem for videos."""
    try:
        path = request.args.get('path', '')
        proc = get_processor()
        
        # Start from input directory if no path specified
        if not path:
            base_path = proc.file_manager.path_config.input_dir
        else:
            base_path = Path(path)
        
        # Security: ensure path is within input directory
        input_dir = proc.file_manager.path_config.input_dir
        try:
            base_path.relative_to(input_dir)
        except ValueError:
            return jsonify({'error': 'Access denied'}), 403
        
        if not base_path.exists():
            return jsonify({'error': 'Path not found'}), 404
        
        items = []
        
        # Add parent directory link if not at root
        if base_path != input_dir:
            items.append({
                'name': '..',
                'path': str(base_path.parent),
                'type': 'directory'
            })
        
        # List directories and video files
        try:
            for item in sorted(base_path.iterdir()):
                # Skip Synology metadata
                if proc.file_manager._is_synology_metadata_path(item):
                    continue
                
                if item.is_dir():
                    items.append({
                        'name': item.name,
                        'path': str(item),
                        'type': 'directory'
                    })
                elif item.suffix.lower() in proc.file_manager.processing_config.video_extensions:
                    items.append({
                        'name': item.name,
                        'path': str(item),
                        'type': 'file',
                        'size': item.stat().st_size
                    })
        except PermissionError:
            return jsonify({'error': 'Permission denied'}), 403
        
        return jsonify({
            'current_path': str(base_path),
            'items': items
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/video-comparison')
def api_video_comparison():
    """Get side-by-side comparison of input vs output videos."""
    try:
        proc = get_processor()
        input_dir = proc.file_manager.path_config.input_dir
        output_dir = proc.file_manager.path_config.output_dir
        extensions = proc.file_manager.processing_config.video_extensions
        
        # Get all input videos (excluding Synology metadata)
        input_videos = set()
        for ext in extensions:
            for p in input_dir.rglob(f'*{ext}'):
                if '@eaDir' not in str(p):
                    # Store relative path from input_dir
                    rel_path = p.relative_to(input_dir)
                    input_videos.add(str(rel_path))
        
        # Get all output videos (excluding Synology metadata)
        output_videos = set()
        for ext in extensions:
            for p in output_dir.rglob(f'*{ext}'):
                if '@eaDir' not in str(p):
                    # Store relative path from output_dir
                    rel_path = p.relative_to(output_dir)
                    output_videos.add(str(rel_path))
        
        # Build comparison list
        all_paths = sorted(input_videos | output_videos)
        comparison = []
        
        matched = 0
        missing_output = 0
        orphaned_output = 0
        
        for rel_path in all_paths:
            in_input = rel_path in input_videos
            in_output = rel_path in output_videos
            
            if in_input and in_output:
                status = 'matched'
                matched += 1
            elif in_input and not in_output:
                status = 'missing_output'
                missing_output += 1
            else:
                status = 'orphaned_output'
                orphaned_output += 1
            
            comparison.append({
                'input': rel_path if in_input else None,
                'output': rel_path if in_output else None,
                'status': status
            })
        
        return jsonify({
            'comparison': comparison,
            'stats': {
                'total_input': len(input_videos),
                'total_output': len(output_videos),
                'matched': matched,
                'missing_output': missing_output,
                'orphaned_output': orphaned_output
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/wordlist')
def api_get_wordlist():
    """Get profanity word list."""
    try:
        proc = get_processor()
        word_list_path = proc.settings.get_word_list_path()
        
        if not word_list_path.exists():
            return jsonify({'error': 'Word list not found'}), 404
        
        with open(word_list_path, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        return jsonify({
            'words': words,
            'count': len(words)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/wordlist', methods=['POST'])
def api_update_wordlist():
    """Update profanity word list."""
    try:
        data = request.json
        words = data.get('words', [])
        
        if not isinstance(words, list):
            return jsonify({'error': 'words must be a list'}), 400
        
        proc = get_processor()
        word_list_path = proc.settings.get_word_list_path()
        
        # Save word list
        with open(word_list_path, 'w', encoding='utf-8') as f:
            f.write('# Profanity word list\n')
            f.write('# One word per line\n')
            f.write('# Wildcards: * (any characters), ? (single character)\n\n')
            for word in words:
                if word.strip():
                    f.write(f"{word.strip()}\n")
        
        # Reload profanity detector
        proc.reload_config()
        
        return jsonify({
            'success': True,
            'count': len(words),
            'message': f'Updated word list with {len(words)} words'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Scene Editor API Endpoints

@app.route('/scene_editor.html')
def scene_editor():
    """Serve the scene editor HTML."""
    return send_from_directory('static', 'scene_editor.html')


@app.route('/api/scene-filters')
def api_get_all_scene_filters():
    """Get all scene filters."""
    try:
        from cleanvid.services.scene_manager import SceneManager
        
        proc = get_processor()
        scene_mgr = SceneManager(proc.settings.paths.config_dir)
        
        filters = scene_mgr.load_scene_filters()
        stats = scene_mgr.get_filter_statistics()
        
        # Convert to dict for JSON
        filters_dict = {}
        for video_path, video_filters in filters.items():
            filters_dict[video_path] = video_filters.to_dict()
        
        return jsonify({
            'filters': filters_dict,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scene-filters/<path:video_path>')
def api_get_video_scene_filters(video_path):
    """Get scene filters for a specific video."""
    try:
        from cleanvid.services.scene_manager import SceneManager
        
        proc = get_processor()
        scene_mgr = SceneManager(proc.settings.paths.config_dir)
        
        # Decode path
        video_path = '/' + video_path
        
        filters = scene_mgr.get_video_filters(video_path)
        
        if filters is None:
            return jsonify({
                'video_path': video_path,
                'skip_zones': [],
                'zone_count': 0
            })
        
        return jsonify(filters.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scene-filters/<path:video_path>', methods=['POST'])
def api_save_video_scene_filters(video_path):
    """Save/update scene filters for a video."""
    try:
        from cleanvid.services.scene_manager import SceneManager
        from cleanvid.models.scene import SkipZone, parse_timestamp
        
        data = request.json
        skip_zones_data = data.get('skip_zones', [])
        
        proc = get_processor()
        scene_mgr = SceneManager(proc.settings.paths.config_dir)
        
        # Decode path
        video_path = '/' + video_path
        
        # Load existing filters
        filters = scene_mgr.load_scene_filters()
        
        # Parse skip zones from request
        skip_zones = []
        for zone_data in skip_zones_data:
            try:
                # Parse timestamps from display format
                start_time = parse_timestamp(zone_data.get('start_display', zone_data.get('start_time', '0:00')))
                end_time = parse_timestamp(zone_data.get('end_display', zone_data.get('end_time', '0:01')))
                
                # Create zone with both time formats
                zone = SkipZone(
                    id=zone_data.get('id'),
                    start_time=start_time,
                    end_time=end_time,
                    start_display=zone_data.get('start_display', '0:00'),
                    end_display=zone_data.get('end_display', '0:01'),
                    description=zone_data.get('description', ''),
                    mode=zone_data.get('mode', 'skip'),
                    mute=zone_data.get('mute', False)
                )
                skip_zones.append(zone)
            except Exception as e:
                return jsonify({'error': f'Invalid skip zone data: {e}'}), 400
        
        # Create or update video filters
        from cleanvid.models.scene import VideoSceneFilters
        video_filters = VideoSceneFilters(
            video_path=video_path,
            title=data.get('title', ''),
            skip_zones=skip_zones
        )
        
        filters[video_path] = video_filters
        
        # Save
        if scene_mgr.save_scene_filters(filters):
            return jsonify({
                'success': True,
                'message': f'Saved {len(skip_zones)} skip zone(s)',
                'filters': video_filters.to_dict()
            })
        else:
            return jsonify({'error': 'Failed to save filters'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scene-filters/<path:video_path>', methods=['DELETE'])
def api_delete_video_scene_filters(video_path):
    """Delete all scene filters for a video."""
    try:
        from cleanvid.services.scene_manager import SceneManager
        
        proc = get_processor()
        scene_mgr = SceneManager(proc.settings.paths.config_dir)
        
        # Decode path
        video_path = '/' + video_path
        
        if scene_mgr.delete_video_filters(video_path):
            return jsonify({
                'success': True,
                'message': 'Filters deleted'
            })
        else:
            return jsonify({'error': 'No filters found for video'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scene-filters/<path:video_path>/<zone_id>', methods=['DELETE'])
def api_delete_skip_zone(video_path, zone_id):
    """Delete a specific skip zone."""
    try:
        from cleanvid.services.scene_manager import SceneManager
        
        proc = get_processor()
        scene_mgr = SceneManager(proc.settings.paths.config_dir)
        
        # Decode path
        video_path = '/' + video_path
        
        if scene_mgr.delete_skip_zone(video_path, zone_id):
            return jsonify({
                'success': True,
                'message': 'Skip zone deleted'
            })
        else:
            return jsonify({'error': 'Skip zone not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Queue API Endpoints

@app.route('/api/scene-queue')
def api_get_scene_queue():
    """Get scene processing queue."""
    try:
        from cleanvid.services.queue_manager import QueueManager
        
        proc = get_processor()
        queue_mgr = QueueManager(proc.settings.paths.config_dir)
        
        queue = queue_mgr.get_queue()
        
        return jsonify({
            'queue': queue,
            'size': len(queue)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scene-queue', methods=['POST'])
def api_add_to_scene_queue():
    """Add video to scene processing queue."""
    try:
        from cleanvid.services.queue_manager import QueueManager
        
        data = request.json
        video_path = data.get('video_path')
        priority = data.get('priority', 0)
        
        if not video_path:
            return jsonify({'error': 'video_path required'}), 400
        
        proc = get_processor()
        queue_mgr = QueueManager(proc.settings.paths.config_dir)
        
        if queue_mgr.add_to_queue(video_path, priority):
            return jsonify({
                'success': True,
                'message': 'Added to queue',
                'queue_size': queue_mgr.get_queue_size()
            })
        else:
            return jsonify({'error': 'Already in queue or failed to add'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scene-queue/<path:video_path>', methods=['DELETE'])
def api_remove_from_scene_queue(video_path):
    """Remove video from scene processing queue."""
    try:
        from cleanvid.services.queue_manager import QueueManager
        
        proc = get_processor()
        queue_mgr = QueueManager(proc.settings.paths.config_dir)
        
        # Decode path
        video_path = '/' + video_path
        
        if queue_mgr.remove_from_queue(video_path):
            return jsonify({
                'success': True,
                'message': 'Removed from queue'
            })
        else:
            return jsonify({'error': 'Not in queue'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scene-queue/process', methods=['POST'])
def api_process_scene_queue():
    """Process all videos in scene queue."""
    try:
        from cleanvid.services.queue_manager import QueueManager
        
        proc = get_processor()
        queue_mgr = QueueManager(proc.settings.paths.config_dir)
        
        queue = queue_mgr.get_queue()
        
        if not queue:
            return jsonify({
                'success': True,
                'message': 'Queue is empty',
                'processed': 0
            })
        
        # Process each video in queue
        results = []
        for entry in queue:
            video_path = entry['video_path']
            try:
                # Process video (will use scene filters if they exist)
                stats = proc.process_single(Path(video_path))
                results.append({
                    'video_path': video_path,
                    'success': stats.successful > 0,
                    'error': None
                })
            except Exception as e:
                results.append({
                    'video_path': video_path,
                    'success': False,
                    'error': str(e)
                })
        
        # Clear queue after processing
        queue_mgr.clear_queue()
        
        successful = sum(1 for r in results if r['success'])
        
        return jsonify({
            'success': True,
            'processed': len(results),
            'successful': successful,
            'failed': len(results) - successful,
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def extract_error_type(error_msg: str, max_words: int = 5) -> str:
    """Extract error type from error message.
    
    Takes the first N words to group similar errors together,
    ignoring file paths and other unique details.
    """
    if not error_msg:
        return 'Unknown Error'
    
    # Normalize whitespace
    error_msg = error_msg.strip()
    
    # Split into words
    words = error_msg.split()
    
    # Take first N words
    if len(words) <= max_words:
        return error_msg
    
    return ' '.join(words[:max_words]) + '...'


def run_server(host='0.0.0.0', port=8080, debug=False):
    """Run the Flask development server."""
    # Start background queue worker
    start_queue_worker()
    
    try:
        app.run(host=host, port=port, debug=debug)
    finally:
        # Stop worker on shutdown
        stop_queue_worker()


if __name__ == '__main__':
    run_server(debug=True)
