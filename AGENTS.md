# Development Guide for LYRI

LYRI is a music video generation system that creates karaoke/music videos from audio tracks and lyrics.

## Table of Contents
- [Build/Lint/Test](#buildlinttest)
- [Code Style Guidelines](#code-style-guidelines)

## Installation
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Build/Lint/Test

### Linting and Formatting
```bash
ruff check . --fix
black lyri/
mypy lyri/ --ignore-missing-imports
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_<file>.py -v

# Run specific test function
pytest tests/test_<file>.py::test_<function> -v

# Run with coverage
pytest tests/ --cov=lyri --cov-report=html

# Run specific service tests
python -m pytest tests/test_fastapi_server.py -v
python -m pytest tests/test_telegram_bot.py -v
```

### Running Systems
```bash
python telegram_bot.py --config ./configs/default.yaml
uvicorn fastapi_server:app --host 0.0.0.0 --port 8000
```

## Code Structure

### Core Components
- `lyri_core.py`: Main orchestrator
- `audio_processor.py`: Audio processing & vocal separation
- `aligners.py`: Lyrics synchronization
- `video_builder.py`: Video building with ffmpeg
- `subtitles_engine.py`: SRT to ASS conversion
- `config.py`: Configuration management

### Telegram Bot & API
- `telegram_bot.py`: Telegram bot implementation
- `fastapi_server.py`: HTTP API server
- `fastapi_dclient.py`: Client for FastAPI server

### Key Dependencies
- Audio: speechbrain, audio-separator, onnxruntime-gpu
- Video: ffmpeg-python
- Speech: whisperx
- Telegram: python-telegram-bot
- API: fastapi, uvicorn
- Utils: pathlib, structlog, aiohttp

## Code Style Guidelines

### Imports
- Standard library → Third-party → Local
- Group by module, one per line
- Always use absolute imports: `from lyri.utils import foo`

```python
import os
from typing import Optional
import numpy as np
from speechbrain.processing import AudioProcessing

from lyri.config import Config
from lyri.utils.file_utils import ensure_directory
```

### Naming Conventions
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`
- Private: `_prefix`
- Tests: `test_` prefix

### Type Hints
- Required for all parameters and return values
- Use `-> None` for void functions
- Use `Optional[T]` for optional values
- Use `Tuple[T, U]` for tuples

### Error Handling
- Use specific exceptions, never bare `except:`
- Log with `structlog` for errors and debugging
- Return `None` or raise exceptions
- Use `try/except/finally` for resource cleanup
- Include context in log messages (paths, user IDs)

### String & File Operations
- Use f-strings: `f"Value: {value}"`
- Always use UTF-8 for text files
- Use `Path` from pathlib: `Path(file)`

### Async/Await
- All I/O operations must be async
- Use `asyncio.run()` for main entry points
- Use `async with` for context managers
- Name async functions with `_async` suffix

### Logging Levels
- `DEBUG`: Detailed debugging info
- `INFO`: High-level progress
- `WARNING`: Potential issues
- `ERROR`: Affects operation
- `CRITICAL`: Critical failures

### Docstrings
- Follow Google style
- Include: description, parameters (with types), return (with type)
- Add examples for complex functionality

### File Organization
- Keep files < 500 lines when possible
- Split large files into logical modules
- Use `__all__` for public API
- Group related code together

## Architecture Patterns

### Configuration
- Centralized via `config.py`
- Dependency injection for Config objects
- Support YAML and CLI config
- Validate on initialization

### Task Pipeline
1. Audio preprocessing
2. Vocal separation
3. Lyrics alignment
4. Video building

### Error Handling
- Graceful degradation
- User-friendly messages
- Comprehensive logging
- Retry logic for transient failures
- Custom exceptions for app-specific errors

### Async Pattern
- Use `asyncio` for concurrency
- Prefer async libraries (aiohttp)
- Limit thread pool for I/O operations
- Properly handle task cancellation