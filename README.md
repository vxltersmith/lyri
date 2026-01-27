# LYRI - Music Video Generation System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

LYRI is a music video generation system that creates karaoke/music videos from audio tracks and lyrics using advanced AI models for vocals separation and lyrics synchronization.

## Features

- 🎵 **Audio Processing**: Process audio files with vocal separation
- 🔊 **Vocal Separation**: AI-powered vocals and instrumentals separation
- 📝 **Lyrics Alignment**: Synchronize lyrics with audio timestamps
- 🎬 **Video Generation**: Create subtitled karaoke videos
- 🤖 **Telegram Bot**: Process requests via Telegram chat
- 🌐 **REST API**: HTTP interface for video generation

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Examples](#examples)
- [Architecture](#architecture)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

- Python 3.8+
- Git
- FFmpeg (for video processing)
- GPU recommended (CUDA/cuDNN for faster processing)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/anomalyco/lyri.git
cd lyri

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pre-commit install
```

### Using Docker (Commercial Implementation)

```bash
# Build the Docker image
docker build -t lyri .

# Run the container
docker run -d -p 8000:8000 --name lyri lyri
```

## Usage

### Telegram Bot

```bash
python telegram_bot.py --config ./configs/default.yaml
```

### FastAPI Server

```bash
uvicorn fastapi_server:app --host 0.0.0.0 --port 8000
```

### CLI Processing

```bash
# Generate video from audio and lyrics
python lyri_core.py \
  --audio_path song.mp3 \
  --lyrics_path lyrics.srt \
  --output_path output.mp4
```

## Configuration

LYRI uses YAML configuration files with the following options:

```yaml
# Example configuration in configs/default.yaml
audio:
  sample_rate: 16000
  model_path: models/vocals-separator.onnx
  output_dir: outputs
video:
  fps: 30
  width: 1280
  height: 720
  font_path: fonts/NotoSans-Regular.ttf
  background_path: backgrounds/default.jpg
telegram:
  token: YOUR_TELEGRAM_BOT_TOKEN
  allowed_users: [user1, user2]
```

## Examples

### Basic Video Generation

Create a karaoke video from an audio file and SRT subtitles:

```bash
python lyri_core.py \
  --audio_path examples/audio/mysong.mp3 \
  --lyrics_path examples/lyrics/mysong.srt \
  --output_path output/my_video.mp4
```

### Telegram Bot Integration

Start the bot and process song requests:

```bash
python telegram_bot.py \
  --config ./configs/default.yaml \
  --telegram_token YOUR_TOKEN
```

## Architecture

### Core Components

```
┌───────────────────────────────────────────────────────┐
│                 LYRI Architecture                     │
├───────────────────────┬───────────────────────┬─────────┤
│    Audio Processing    │    Lyrics Alignment    │   Video │
│  ┌─────────────────┐   │  ┌─────────────────┐   │ Building│
│  │ Audio Processor │   │  │  Lyrics        │   │         │
│  │ - Load audio     │   │  │  Aligner       │   │  ┌──────┐│
│  │ - Normalize      │   │  │ - SRT/ASV parser │   │  │ ffmpeg│
│  │ - Vocal sep.     │   │  │ - Time alignment│   │  └──────┘│
│  └─────────────────┘   │  └─────────────────┘   │         │
└───────────────────────┴───────────────────────┴─────────┘
                                        │
                                ┌───────────────────────┐
                                │       Config         │
                                │ - YAML configs      │
                                │ - Command line      │
                                │ - Environment vars  │
                                └───────────────────────┘

                                    Main Entry Points:
                                    ▼
                            ┌──────────────┐    ┌──────────────┐
                            │Telegram Bot │    │ FastAPI     │
                            │- Chat        │    │ Server      │
                            │- File        │    │- HTTP API   │
                            │ upload       │    │- Webhooks   │
                            └──────────────┘    └──────────────┘
```

### Processing Pipeline

1. **Audio Preprocessing**: Load and normalize audio files
2. **Vocal Separation**: Split vocals from background using ONNX models
3. **Lyrics Alignment**: Synchronize lyrics with audio timestamps
4. **Video Building**: Overlay subtitles on background video/image
5. **Output Generation**: Save final MP4 file

## Development

### Building and Testing

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Lint code
ruff check .

# Format code
black lyri/
```

### Model Files

LYRI requires ONNX model files for audio processing. Download instructions will be added in a future release.

### Common Issues

- **FFmpeg not found**: Install FFmpeg from your package manager
- **GPU acceleration**: Ensure CUDA/cuDNN are properly installed
- **Memory errors**: Reduce batch size or use CPU mode

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

### Code Style

- Use `black` for formatting
- Use `ruff` for linting
- Use type hints
- Follow PEP 8 guidelines

## Roadmap

- [ ] Model file distribution system
- [ ] Batch processing support
- [ ] Advanced video effects
- [x] Telegram bot integration
- [x] FastAPI HTTP interface
- [x] Core video generation pipeline

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Questions?

Join our [Discord community](https://discord.gg/lyri) or open an issue on GitHub.
