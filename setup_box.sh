#!/bin/bash
# One-shot setup for a fresh Vast.ai GPU box (PyTorch template, CUDA 13).
# Run from /workspace after: git clone https://github.com/Abdrehman2002/Build3.git
# Usage:  bash /workspace/Build3/setup_box.sh
set -e
cd /workspace

echo "=== [1/5] System deps ==="
apt-get update && apt-get install -y ffmpeg git tmux

echo "=== [2/5] Model-serving packages ==="
pip install -U pip huggingface_hub hf_transfer
pip install vllm faster-whisper snac
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12   # faster-whisper needs CUDA-12 libs on a CUDA-13 box

echo "=== [3/5] Agent + LiveKit packages ==="
cd /workspace/Build3
pip install -r requirements.txt
pip install aiohttp
python -m livekit.agents download-files            # turn-detector model
cd /workspace

echo "=== [4/5] Download models (Qwen2.5-72B + Whisper + Orpheus) ==="
mkdir -p /workspace/models
export HF_HUB_ENABLE_HF_TRANSFER=1
hf download Qwen/Qwen2.5-72B-Instruct-AWQ --local-dir /workspace/models/qwen72
hf download Systran/faster-whisper-large-v3 --local-dir /workspace/models/whisper
hf download mahwizzzz/orpheus-urdu-tts      --local-dir /workspace/models/orpheus-hf

echo "=== [5/5] Place server scripts ==="
cp /workspace/Build3/stt_server.py /workspace/stt_server.py
cp /workspace/Build3/tts_server.py /workspace/tts_server.py

echo ""
echo "=== SETUP COMPLETE ==="
echo "Next: create /workspace/Build3/.env, then run:"
echo "  bash /workspace/Build3/start_servers.sh"
