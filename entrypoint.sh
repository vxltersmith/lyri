#!/bin/bash
set -e

mkdir -p /app/checkpoints/vocal_separator
mkdir -p /app/cache/huggingface
mkdir -p /app/cache/torch
mkdir -p /app/server_data/inputs_cache
mkdir -p /app/server_data/aligner_cache

MODEL_PATH="/app/checkpoints/vocal_separator/Kim_Vocal_2.onnx"
if [ ! -f "$MODEL_PATH" ]; then
    echo "Downloading Kim_Vocal_2.onnx..."
    curl -L -o "$MODEL_PATH" \
        "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/Kim_Vocal_2.onnx"
fi

case "$1" in
    server) exec python3 -m uvicorn fastapi_server:app --host 0.0.0.0 --port 8000 ;;
    bot) exec python3 telegram_bot.py --config ./configs/default.yaml ;;
    *) exec "$@" ;;
esac
