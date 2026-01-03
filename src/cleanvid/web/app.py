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

from cleanvid.services.processor import Processor
from cleanvid.services.config_manager import ConfigManager


app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize processor
processor = None


def get_processor():
    """Get or create processor instance."""
    global processor
    if processor is None:
        processor = Processor()
    return processor


@app.route('/')
def index():
    """Serve the dashboard HTML."""
    return send_from_directory('static', 'dashboard.html')


@app.route('/queue.html')
def queue_page():
    """Serve the queue HTML."""
    return send_from_directory('static', 'queue.html')


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
        
        # Group by error type
        error_groups = {}
        for failure in failures:
            error = failure.get('error', 'Unknown error')
            error_type = classify_error(error)
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
    """Process a specific video."""
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
        
        # Process it
        stats = proc.process_single(video_path)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_videos': stats.total_videos,
                'successful': stats.successful,
                'failed': stats.failed,
                'skipped': stats.skipped
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process-all', methods=['POST'])
def api_process_all():
    """Process all unprocessed videos."""
    try:
        proc = get_processor()
        
        # Get count of unprocessed videos
        unprocessed_count = len(proc.file_manager.get_unprocessed_videos())
        
        if unprocessed_count == 0:
            return jsonify({
                'success': True,
                'message': 'No unprocessed videos found',
                'stats': {
                    'total_videos': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0
                }
            })
        
        # Process all unprocessed videos
        stats = proc.process_batch(max_videos=unprocessed_count)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_videos': stats.total_videos,
                'successful': stats.successful,
                'failed': stats.failed,
                'skipped': stats.skipped
            },
            'message': f'Processed {stats.total_videos} videos: {stats.successful} successful, {stats.failed} failed'
        })
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
    """Bypass multiple videos by copying to output."""
    try:
        data = request.json
        video_paths = data.get('video_paths', [])
        
        if not video_paths:
            return jsonify({'error': 'video_paths required'}), 400
        
        proc = get_processor()
        paths = [Path(p) for p in video_paths]
        
        result = proc.bypass_multiple_videos(paths)
        
        return jsonify({
            'success': True,
            'result': result,
            'message': f"Bypassed {result['successful']} of {result['total']} videos"
        })
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


def classify_error(error_msg: str) -> str:
    """Classify error message into category."""
    error_lower = error_msg.lower()
    
    if 'encoding' in error_lower or 'utf-8' in error_lower or 'decode' in error_lower:
        return 'Encoding Error'
    elif 'subtitle' in error_lower and 'not found' in error_lower:
        return 'Missing Subtitle'
    elif 'subtitle' in error_lower and 'empty' in error_lower:
        return 'Empty Subtitle'
    elif 'ffmpeg' in error_lower:
        return 'FFmpeg Error'
    elif 'directory' in error_lower or '@eadir' in error_lower:
        return 'Invalid Path'
    elif 'not found' in error_lower:
        return 'File Not Found'
    else:
        return 'Other Error'


def run_server(host='0.0.0.0', port=8080, debug=False):
    """Run the Flask development server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)
