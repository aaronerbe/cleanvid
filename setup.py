"""
Cleanvid - Automated Movie Profanity Filter

A tool for automatically filtering profanity from movies by analyzing subtitles
and muting audio at detected timestamps.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="cleanvid",
    version="1.0.0",
    description="Automated movie profanity filter using subtitle analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Aaron",
    author_email="",
    url="https://github.com/yourusername/cleanvid",
    license="MIT",
    
    # Package configuration
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=requirements,
    
    # Entry points
    entry_points={
        "console_scripts": [
            "cleanvid=cleanvid.cli.main:main",
        ],
    },
    
    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    
    # Additional metadata
    keywords="video profanity filter subtitle jellyfin plex",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/cleanvid/issues",
        "Source": "https://github.com/yourusername/cleanvid",
    },
)
