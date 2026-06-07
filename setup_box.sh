#!/bin/bash
# One-shot setup for a fresh GPU box (PyTorch template, CUDA 12.x).
# Target: single 48GB card (e.g. L40S/A6000). Stack = Qwen-14B LLM + Whisper STT
# on the GPU; TTS is OFF-box via Uplift AI cloud API (no local TTS server).
# Run from /workspace after: git clone https://github.com/Abdrehman2002/Build3.git
# Usage:  bash /workspace/Build3/setup_box.sh
set -e
cd /workspace

echo "=== [1/4] System deps ==="
apt-get update && apt-get install -y ffmpeg git tmux

echo "=== [2/4] Model-serving packages ==="
pip install -U pip huggingface_hub hf_transfer
pip install vllm faster-whisper
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12   # faster-whisper needs these CUDA-12 libs

echo "=== [3/4] Agent + LiveKit packages (incl. livekit-plugins-upliftai) ==="
cd /workspace/Build3
pip install -r requirements.txt
pip install aiohttp
python -m livekit.agents download-files            # turn-detector model
cd /workspace

echo "=== [4/4] Download models (Qwen2.5-14B-AWQ + Whisper large-v3) ==="
mkdir -p /workspace/models
export HF_HUB_ENABLE_HF_TRANSFER=1
hf download Qwen/Qwen2.5-14B-Instruct-AWQ   --local-dir /workspace/models/qwen14
hf download Systran/faster-whisper-large-v3 --local-dir /workspace/models/whisper

echo "=== Place STT server script ==="
cp /workspace/Build3/stt_server.py /workspace/stt_server.py

echo ""
echo "=== SETUP COMPLETE ==="
echo "Next: create /workspace/Build3/.env, then run:"
echo "  bash /workspace/Build3/start_servers.sh"
