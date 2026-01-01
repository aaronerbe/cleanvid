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
        history = proc.get_recent_history(limit=100)
        
        failures = [
            entry for entry in history
            if not entry.get('success', False)
        ]
        
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
        
        # Check if last processing was within last 5 minutes
        if recent_history:
            last_entry = recent_history[0]
            last_time = datetime.fromisoformat(last_entry['timestamp'])
            time_diff = (datetime.now() - last_time).total_seconds()
            
            is_processing = time_diff < 300  # 5 minutes
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
