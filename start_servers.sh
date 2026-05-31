#!/bin/bash
# Start the three self-hosted model servers in tmux sessions.
# Usage:  bash /workspace/Build3/start_servers.sh
cd /workspace

echo "Starting LLM (Qwen2.5-72B) on :8001 ..."
tmux kill-session -t llm 2>/dev/null
tmux new -s llm -d 'vllm serve /workspace/models/qwen72 --served-model-name sara-llm --max-model-len 4096 --gpu-memory-utilization 0.65 --enable-auto-tool-choice --tool-call-parser hermes --port 8001 2>&1 | tee /workspace/llm.log'

echo "Starting STT (Whisper) on :8002 ..."
NVLIBS=$(python -c "import nvidia,glob;base=list(nvidia.__path__)[0];print(':'.join(glob.glob(base+'/*/lib')))")
tmux kill-session -t stt 2>/dev/null
tmux new -s stt -d "cd /workspace && LD_LIBRARY_PATH=$NVLIBS uvicorn stt_server:app --host 0.0.0.0 --port 8002 2>&1 | tee /workspace/stt.log"

echo "Starting TTS (Orpheus) on :8003 ..."
tmux kill-session -t tts 2>/dev/null
tmux new -s tts -d 'cd /workspace && uvicorn tts_server:app --host 0.0.0.0 --port 8003 2>&1 | tee /workspace/tts.log'

echo ""
echo "All three servers launching in tmux (llm, stt, tts)."
echo "Qwen-72B takes ~5-8 min to load. Watch:  tail -n 6 /workspace/llm.log"
echo "Then run the agent:  cd /workspace/Build3 && tmux new -s agent -d 'python agent.py dev 2>&1 | tee /workspace/agent.log'"
