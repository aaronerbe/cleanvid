"""
Command-line interface for cleanvid.

Provides commands for processing videos, managing configuration, and viewing status.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from cleanvid.services.processor import Processor
from cleanvid.utils.logger import setup_logging, get_logger


def cmd_init(args):
    """Initialize cleanvid configuration."""
    from cleanvid.services.config_manager import ConfigManager
    
    config_dir = Path(args.config) if args.config else None
    config_manager = ConfigManager(config_dir=config_dir)
    
    print("Initializing cleanvid configuration...")
    config_manager.initialize_config_directory()
    
    print(f"✓ Configuration initialized at: {config_manager.config_dir}")
    print(f"\nNext steps:")
    print(f"1. Edit configuration: {config_manager.config_file}")
    print(f"2. Edit word list: {config_manager.config_dir / 'profanity_words.txt'}")
    print(f"3. Run: cleanvid status")


def cmd_status(args):
    """Show current status."""
    config_dir = Path(args.config) if args.config else None
    processor = Processor(config_path=config_dir)
    
    processor.print_status()


def cmd_process(args):
    """Process videos."""
    config_dir = Path(args.config) if args.config else None
    processor = Processor(config_path=config_dir)
    
    # Single video mode
    if args.video:
        video_path = Path(args.video)
        if not video_path.exists():
            print(f"Error: Video file not found: {video_path}")
            sys.exit(1)
        
        stats = processor.process_single(video_path)
    
    # Batch mode
    else:
        max_videos = args.max_videos
        max_time = args.max_time
        force = args.force
        
        stats = processor.process_batch(
            max_videos=max_videos,
            max_time_minutes=max_time,
            force_reprocess=force
        )
    
    # Print summary
    print("\n" + "="*60)
    print("Processing Summary")
    print("="*60)
    print(stats.to_summary_string())


def cmd_history(args):
    """Show processing history."""
    config_dir = Path(args.config) if args.config else None
    processor = Processor(config_path=config_dir)
    
    limit = args.limit
    history = processor.get_recent_history(limit=limit)
    
    if not history:
        print("No processing history found.")
        return
    
    print(f"\n{'='*80}")
    print(f"Processing History (Most Recent {len(history)})")
    print(f"{'='*80}\n")
    
    for entry in history:
        timestamp = entry.get('timestamp', 'Unknown')
        video = Path(entry.get('video_path', 'Unknown')).name
        success = entry.get('success', False)
        segments = entry.get('segments_muted', 0)
        error = entry.get('error', '')
        
        status_symbol = "✓" if success else "✗"
        status_text = "SUCCESS" if success else "FAILED"
        
        print(f"{status_symbol} {timestamp[:19]} | {status_text:7} | {video}")
        if success and segments > 0:
            print(f"  Segments muted: {segments}")
        if error:
            print(f"  Error: {error}")
        print()


def cmd_reset(args):
    """Reset processing status for a video or videos."""
    config_dir = Path(args.config) if args.config else None
    processor = Processor(config_path=config_dir)
    
    # Handle --filter option
    if args.filter:
        if args.filter == 'failed':
            count = processor.reset_failed_videos()
            if count > 0:
                print(f"✓ Reset {count} failed video(s)")
                print(f"  These videos will be reprocessed on next run.")
            else:
                print("No failed videos found.")
        elif args.filter == 'all':
            # Reset all processed videos
            processor.file_manager.clear_processed_log()
            print("✓ Reset all processed videos")
            print("  All videos will be reprocessed on next run.")
        else:
            print(f"✗ Invalid filter: {args.filter}")
            print("  Valid filters: failed, all")
            sys.exit(1)
    else:
        # Reset specific video
        if not args.video:
            print("✗ Error: Either specify a video file or use --filter")
            sys.exit(1)
        
        video_path = Path(args.video)
        
        if processor.reset_video(video_path):
            print(f"✓ Reset processing status for: {video_path.name}")
            print(f"  Video will be reprocessed on next run.")
        else:
            print(f"✗ Video was not marked as processed: {video_path.name}")
            sys.exit(1)


def cmd_config(args):
    """Show or edit configuration."""
    from cleanvid.services.config_manager import ConfigManager
    
    config_dir = Path(args.config) if args.config else None
    config_manager = ConfigManager(config_dir=config_dir)
    
    if args.show:
        # Show configuration summary
        print(config_manager.get_config_summary())
    
    elif args.validate:
        # Validate configuration
        is_valid, errors = config_manager.validate_config()
        
        if is_valid:
            print("✓ Configuration is valid")
        else:
            print("✗ Configuration has errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    
    else:
        # Show config file location
        print(f"Configuration file: {config_manager.config_file}")
        print(f"Word list: {config_manager.config_dir / 'profanity_words.txt'}")
        print(f"\nTo edit configuration:")
        print(f"  nano {config_manager.config_file}")
        print(f"\nTo validate configuration:")
        print(f"  cleanvid config --validate")


def cmd_web(args):
    """Start web dashboard."""
    print(f"Starting Cleanvid web dashboard on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    from cleanvid.web.app import run_server
    run_server(host=args.host, port=args.port, debug=args.verbose)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanvid - Automated movie profanity filtering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cleanvid init                          Initialize configuration
  cleanvid status                        Show system status
  cleanvid process                       Process batch (respects limits)
  cleanvid process --max-time 300        Process for 5 hours
  cleanvid process movie.mkv             Process single video
  cleanvid history                       Show recent processing
  cleanvid reset movie.mkv               Reset video status
  cleanvid config --validate             Validate configuration
  cleanvid web                           Start web dashboard

For more information: https://github.com/yourusername/cleanvid
        """
    )
    
    # Global arguments
    parser.add_argument(
        '--config',
        metavar='DIR',
        help='Configuration directory (default: /config)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress console output (file logging only)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='cleanvid 1.0.0'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # init command
    parser_init = subparsers.add_parser(
        'init',
        help='Initialize configuration'
    )
    parser_init.set_defaults(func=cmd_init)
    
    # status command
    parser_status = subparsers.add_parser(
        'status',
        help='Show current status'
    )
    parser_status.set_defaults(func=cmd_status)
    
    # process command
    parser_process = subparsers.add_parser(
        'process',
        help='Process videos'
    )
    parser_process.add_argument(
        'video',
        nargs='?',
        help='Process specific video file'
    )
    parser_process.add_argument(
        '--max-videos',
        type=int,
        metavar='N',
        help='Maximum number of videos to process'
    )
    parser_process.add_argument(
        '--max-time',
        type=int,
        metavar='MINUTES',
        help='Maximum processing time in minutes'
    )
    parser_process.add_argument(
        '--force',
        action='store_true',
        help='Reprocess already processed videos'
    )
    parser_process.set_defaults(func=cmd_process)
    
    # history command
    parser_history = subparsers.add_parser(
        'history',
        help='Show processing history'
    )
    parser_history.add_argument(
        '--limit',
        type=int,
        default=20,
        metavar='N',
        help='Number of entries to show (default: 20)'
    )
    parser_history.set_defaults(func=cmd_history)
    
    # reset command
    parser_reset = subparsers.add_parser(
        'reset',
        help='Reset processing status for video(s)'
    )
    parser_reset.add_argument(
        'video',
        nargs='?',
        help='Video file to reset'
    )
    parser_reset.add_argument(
        '--filter',
        choices=['failed', 'all'],
        help='Reset multiple videos: "failed" (only failed videos) or "all" (all processed videos)'
    )
    parser_reset.set_defaults(func=cmd_reset)
    
    # config command
    parser_config = subparsers.add_parser(
        'config',
        help='Show or validate configuration'
    )
    parser_config.add_argument(
        '--show',
        action='store_true',
        help='Show configuration summary'
    )
    parser_config.add_argument(
        '--validate',
        action='store_true',
        help='Validate configuration'
    )
    parser_config.set_defaults(func=cmd_config)
    
    # web command
    parser_web = subparsers.add_parser(
        'web',
        help='Start web dashboard'
    )
    parser_web.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port to run web server (default: 8080)'
    )
    parser_web.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser_web.set_defaults(func=cmd_web)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    console_output = not args.quiet
    
    # Determine log file path
    if args.config:
        log_file = Path(args.config) / "logs" / "cleanvid.log"
    else:
        log_file = Path("/logs/cleanvid.log")
    
    setup_logging(
        log_file=log_file,
        log_level=log_level,
        console_output=console_output
    )
    
    logger = get_logger()
    
    # Show help if no command
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Run command
    try:
        logger.debug(f"Running command: {args.command}")
        args.func(args)
        logger.debug(f"Command {args.command} completed successfully")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        logger.info("User interrupted operation")
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {e}")
        logger.error(f"Command {args.command} failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
