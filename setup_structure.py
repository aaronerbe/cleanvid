#!/usr/bin/env python3
"""
Setup script to create the cleanvid project structure
"""
import os
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent

# Define directory structure
DIRECTORIES = [
    # Source code
    "src/config",
    "src/subtitle",
    "src/profanity",
    "src/video",
    "src/queue",
    "src/state",
    "src/utils",
    
    # Tests
    "tests/test_subtitle",
    "tests/test_profanity",
    "tests/test_video",
    "tests/test_queue",
    "tests/test_state",
    "tests/test_integration",
    
    # Docker
    "docker",
    
    # Config
    "config",
    
    # Scripts
    "scripts",
    
    # Docs
    "docs",
    
    # Logs (for local testing)
    "logs",
]

def create_directories():
    """Create all project directories"""
    for directory in DIRECTORIES:
        dir_path = PROJECT_ROOT / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}")
        
        # Create __init__.py for Python packages
        if directory.startswith("src/") or directory.startswith("tests/"):
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.write_text('"""Package initialization."""\n')
                print(f"  ✓ Created: {directory}/__init__.py")

if __name__ == "__main__":
    print("Creating cleanvid project structure...\n")
    create_directories()
    print("\n✅ Project structure created successfully!")
