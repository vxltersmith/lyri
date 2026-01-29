# LYRI - Music Video Generation System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

LYRI creates karaoke/music videos from audio tracks, musical video and optional lyrics of the song.
It uses AI models for vocal separation and lyrics synchronization,
with interfaces for Telegram and HTTP APIs. 
It can recognize and\or align lyrics with musical audio file, create astonishing subtitle or lyrics video as output. 

Project is the mostly core logic server and telegram bot as demo, any contributions are welcome 

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

> 👨‍💻 For developers: See [AGENTS.md](AGENTS.md) for detailed
workflows and coding standards.

## Features

- 🎵 Audio processing with vocal separation
- 🔊 AI-powered dual-track extraction
- 📝 Lyrics synchronization
- 🎬 Karaoke video generation
- 🤖 Telegram bot integration
- 🌐 REST API endpoints

## Docker

### Developer Mode (clone + build)

```bash
git clone https://github.com/vxltersmith/lyri.git
cd lyri
docker compose up -d lyri-server
```

Builds from local `Dockerfile` (CUDA). Changes to source code apply on rebuild.

With Telegram bot:

```bash
TELEGRAM_BOT_TOKEN=your_token docker compose --profile bot up -d
```

### User Mode (pre-built image, no clone needed)

Create `docker-compose.yml`:

```yaml
services:
  lyri-server:
    image: ghcr.io/vxltersmith/lyri:universal
    ports:
      - "8000:8000"
    volumes:
      - lyri-checkpoints:/app/checkpoints
      - lyri-cache:/app/cache
      - lyri-data:/app/server_data

volumes:
  lyri-checkpoints:
  lyri-cache:
  lyri-data:
```

For NVIDIA GPU, use `ghcr.io/vxltersmith/lyri:cuda` and add GPU reservations:

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

Then:

```bash
docker compose up -d
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) for details.
