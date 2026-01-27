# Development Guide for LYRI

LYRI is a music video generation system that creates karaoke/music videos from audio tracks and lyrics.

## Table of Contents
- [Code Structure](#code-structure)
- [Build/Lint/Test](#build-lint-test)
- [Code Style Guidelines](#code-style-guidelines)
- [Architecture Pattern](#architecture-pattern)
- [Project Management](#project-management)

## Code Structure

### Core Components
- **`lyri_core.py`**: Main orchestrator that coordinates audio processing, lyrics alignment, and video building
- **`audio_processor.py`**: Handles audio file processing and vocal separation using ONNX models
- **`aligners.py`**: Contains `LyricsAligner` and `LyricsAlignerWithWhisper` classes for synchronizing lyrics with audio
- **`video_builder.py`**: Builds final videos using ffmpeg with subtitles overlay
- **`subtitles_engine.py`**: Converts SRT subtitles to ASS format for advanced animations
- **`config.py`**: Configuration management system

### Telegram Bot Components
- **`telegram_bot.py`**: Main Telegram bot implementation
- **`fastapi_server.py`**: HTTP API server for processing tasks
- **`fastapi_dclient.py`**: Client for communicating with FastAPI server

## Build/Lint/Test 

### Installation
```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Linting and Formatting
```bash
# Run ruff linter
ruff check .

# Run black formatter
black lyri/

# Run mypy type checker
mypy lyri/ --ignore-missing-imports
```

### Running the System
```bash
python telegram_bot.py --config ./configs/default.yaml
```

### Running the API Server
```bash
uvicorn fastapi_server:app --host 0.0.0.0 --port 8000
```

### Running Tests
```bash
pytest tests/ -v
```

## Code Style Guidelines

### Python-Specific Rules

#### Imports
- Standard library imports first
- Third-party imports second
- Local application imports third
- Group imports by module
- One import per line

#### Naming Conventions
- `snake_case` for variables and functions
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Descriptive names indicating purpose

#### Type Hints
- Use type hints for all function parameters and return values
- For complex return types, use `Tuple` or `Optional`

#### Error Handling
- Use specific exception types rather than bare `except:`
- Logging framework for errors and debugging
- Return `None` or raise exceptions for error conditions

#### String Handling
- Use f-strings or `str.format()` instead of string concatenation
- Be mindful of encoding (UTF-8) when working with text files

#### Async/Await Patterns
- All I/O operations should be async/await
- Use `asyncio.run()` for main entry points
- Properly handle task cancellation

### Architecture Pattern

#### Configuration Management
- Centralized configuration through `config.py`
- Use dependency injection pattern for passing configuration
- Support both command-line and YAML configuration files

#### Task Management
- Each processing task has distinct stages:
  1. Audio preprocessing
  2. Vocal separation
  3. Lyrics alignment
  4. Video building
  
#### Error Handling
- Graceful degradation
- User-friendly error messages
- Comprehensive logging throughout pipeline

### File Organization
- Group related components together
- Clear separation between:
  - Core processing logic
  - Telegram bot interface
  - FastAPI HTTP interface

## Project Management

### Configuration Files
- `configs/default.yaml`: Main configuration
- `configs/server_default.yaml`: Server-specific configuration

### Dependencies
See `requirements.txt` for full dependency list:
- `speechbrain`: Speech processing
- `audio-separator`: Vocal separation
- `onnxruntime-gpu`: ONNX runtime with GPU support
- `ffmpeg-python`: Video processing
- `python-telegram-bot`: Telegram bot framework
- `fastapi`: HTTP API framework
- `uvicorn`: ASGI server
- Additional utilities for text processing, file handling, etc.

### Key Libraries
- Audio processing: speechbrain, audio-separator
- Video processing: ffmpeg-python
- Speech recognition: whisperx
- Telegram bot: python-telegram-bot
- HTTP API: FastAPI

## Development Tips

### Working with Audio Files
- Audio files are processed in WAV format at 16kHz sample rate
- Original files are preserved for reference
- Separated tracks (vocals/instrumentals) stored in cache directories

### Video Generation
- Background support (images or videos)
- Dynamic resolution based on aspect ratio
- SRT subtitles with timestamp alignment

### Configuration Overrides
- Use command-line arguments to override YAML configs
- Supports per-task configuration through `Config.from_user_data()`

### Testing Approach
- Integration testing with real audio/lyrics files
- Manual verification of generated videos
- Check alignment accuracy with known song segments

### Internationalization
- Support for multiple languages in lyrics
- Language detection through config parameters

### Scaling Considerations
- GPU acceleration for audio processing
- Asynchronous I/O operations
- Batch processing support (future enhancement)
