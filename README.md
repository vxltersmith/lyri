# LYRI - Music Video Generation System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

LYRI creates karaoke/music videos from audio tracks and lyrics. It uses AI models for vocal separation and lyrics synchronization, with interfaces for Telegram and HTTP APIs.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run Telegram bot
python telegram_bot.py --config ./configs/default.yaml

# Or run HTTP server
uvicorn fastapi_server:app --host 0.0.0.0 --port 8000
```

## Configuration

LYRI uses YAML configuration files. Key settings in `configs/default.yaml`:

```yaml
# Audio processing
audio:
  sample_rate: 16000
  output_dir: outputs

# Video settings
video:
  fps: 30
  width: 1280
  height: 720
  font_path: fonts/NotoSans-Regular.ttf

# Telegram bot
telegram:
  token: YOUR_TELEGRAM_BOT_TOKEN
  allowed_users: [user1, user2]
```

## Usage Examples

### Basic CLI Usage
```bash
python lyri_core.py \
  --audio_path song.mp3 \
  --lyrics_path lyrics.srt \
  --output_path output.mp4
```

### Telegram Bot
Send audio files and lyrics to the bot through Telegram chat.

### FastAPI Server
Use HTTP endpoints or file uploads to generate videos.

## Requirements

- Python 3.8+
- FFmpeg
- GPU recommended (CUDA/cuDNN)

## Technical Details

- **Audio models**: SpeechBrain, ONNX runtime
- **Video processing**: FFmpeg-python
- **Speech recognition**: WhisperX
- **Integration**: Telegram Bot API, FastAPI

> 👨‍💻 For developers: See [AGENTS.md](AGENTS.md) for detailed workflows and coding standards.

## Features

- 🎵 Audio processing with vocal separation
- 🔊 AI-powered dual-track extraction
- 📝 Lyrics synchronization
- 🎬 Karaoke video generation
- 🤖 Telegram bot integration
- 🌐 REST API endpoints

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.