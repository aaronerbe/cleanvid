# Testing Guide

Quick reference for running tests in the Cleanvid project.

---

## Quick Start

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=src/cleanvid --cov-report=html
```

### Run Specific Test File
```bash
pytest tests/models/test_config.py
pytest tests/services/test_profanity_detector.py
```

### Run Specific Test Class
```bash
pytest tests/models/test_config.py::TestSettings
pytest tests/services/test_config_manager.py::TestConfigManager
```

### Run Specific Test
```bash
pytest tests/models/test_config.py::TestSettings::test_default_settings
```

### Run Tests Matching Pattern
```bash
pytest -k "profanity"  # All tests with "profanity" in name
pytest -k "config"     # All tests with "config" in name
```

---

## Test Markers

### Run Only Unit Tests
```bash
pytest -m unit
```

### Run Only Integration Tests
```bash
pytest -m integration
```

### Skip Slow Tests
```bash
pytest -m "not slow"
```

---

## Verbose Output

### Show Print Statements
```bash
pytest -s
```

### Show Test Names
```bash
pytest -v
```

### Very Verbose (shows all assert details)
```bash
pytest -vv
```

### Show Local Variables on Failure
```bash
pytest -l
```

---

## Common Workflows

### Quick Check (fast tests only)
```bash
pytest -m "not slow" -x
```

### Full Test Suite with Coverage
```bash
pytest --cov=src/cleanvid --cov-report=html --cov-report=term
```

### Debug Failing Test
```bash
pytest -vv -l -s tests/path/to/test.py::test_name
```

### Watch Mode (re-run on file changes) - requires pytest-watch
```bash
ptw
```

---

## Coverage Reports

### Generate HTML Coverage Report
```bash
pytest --cov=src/cleanvid --cov-report=html
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
```

### Show Missing Lines
```bash
pytest --cov=src/cleanvid --cov-report=term-missing
```

### Coverage for Specific Module
```bash
pytest --cov=src/cleanvid/models tests/models/
pytest --cov=src/cleanvid/services tests/services/
```

---

## Test Statistics

### Count Tests
```bash
pytest --collect-only
```

### Show Test Duration
```bash
pytest --durations=10  # Show 10 slowest tests
```

---

## Debugging

### Drop into Debugger on Failure
```bash
pytest --pdb
```

### Drop into Debugger on First Failure
```bash
pytest -x --pdb
```

### Run with Python Debugger
```python
# Add to test:
import pdb; pdb.set_trace()
```

---

## CI/CD Commands

### Full Test Suite (what CI runs)
```bash
pytest --cov=src/cleanvid --cov-report=xml --cov-report=term -v
```

### Type Checking
```bash
mypy src/cleanvid
```

### Linting
```bash
pylint src/cleanvid
```

### Code Formatting Check
```bash
black --check src tests
```

### All Quality Checks
```bash
black --check src tests && \
mypy src/cleanvid && \
pylint src/cleanvid && \
pytest --cov=src/cleanvid --cov-report=term
```

---

## Current Test Statistics

**As of November 28, 2025:**

| Category | Count |
|----------|-------|
| Total Tests | 370+ |
| Model Tests | 280+ |
| Service Tests | 90+ |
| Test Files | 7 |
| Coverage | ~85% |

### Test Files
```
tests/
├── conftest.py (shared fixtures)
├── models/
│   ├── test_config.py (100+ tests)
│   ├── test_subtitle.py (50+ tests)
│   ├── test_segment.py (70+ tests)
│   └── test_processing.py (60+ tests)
└── services/
    ├── test_config_manager.py (40+ tests)
    └── test_profanity_detector.py (50+ tests)
```

---

## Tips

### Parallel Testing (faster)
```bash
# Requires pytest-xdist
pytest -n auto
```

### Only Run Failed Tests from Last Run
```bash
pytest --lf  # last-failed
```

### Run Failed Tests First
```bash
pytest --ff  # failed-first
```

### Stop on First Failure
```bash
pytest -x
```

### Stop After N Failures
```bash
pytest --maxfail=3
```

### Quiet Mode (less output)
```bash
pytest -q
```

---

## Useful Combinations

### Fast Development Cycle
```bash
# Run fast tests, stop on first failure, show output
pytest -m "not slow" -x -s
```

### Pre-Commit Check
```bash
# Format, lint, type check, test
black src tests && \
mypy src/cleanvid && \
pytest --cov=src/cleanvid --cov-report=term
```

### Full Quality Check
```bash
# Everything before pushing to repository
black --check src tests && \
mypy src/cleanvid && \
pylint src/cleanvid && \
pytest --cov=src/cleanvid --cov-report=html --cov-report=term -v
```

---

## Fixtures Reference

Common fixtures available in all tests (from `conftest.py`):

- `temp_video_file` - Temporary video file
- `temp_subtitle_file` - Subtitle file with content
- `sample_subtitle_entries` - List of SubtitleEntry objects
- `sample_mute_segments` - List of MuteSegment objects
- `sample_word_list` - Profanity word list file
- `default_settings` - Default Settings object
- `test_config_dir` - Complete directory structure

### Using Fixtures
```python
def test_example(temp_subtitle_file, sample_word_list):
    """Fixtures are automatically provided by pytest."""
    detector = ProfanityDetector(sample_word_list)
    # ... use fixtures
```

---

## Troubleshooting

### Import Errors
```bash
# Install package in development mode
pip install -e .
```

### Missing Dependencies
```bash
# Install test dependencies
pip install -r requirements-dev.txt
```

### Coverage Not Working
```bash
# Ensure pytest-cov is installed
pip install pytest-cov
```

### Tests Not Found
```bash
# Check PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

## Configuration

The project uses `pytest.ini` for configuration:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --cov=src/cleanvid
    --cov-report=term-missing
    --cov-report=html
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

---

For more information, see the [pytest documentation](https://docs.pytest.org/).
