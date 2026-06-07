#!/bin/bash
# Start the on-GPU model servers in tmux sessions.
# Stack = Qwen-14B LLM (:8001) + Whisper STT (:8002). TTS is OFF-box (Uplift AI),
# so there is no local TTS server here.
# Usage:  bash /workspace/Build3/start_servers.sh
cd /workspace

echo "Starting LLM (Qwen2.5-14B-AWQ) on :8001 ..."
tmux kill-session -t llm 2>/dev/null
tmux new -s llm -d 'vllm serve /workspace/models/qwen14 --served-model-name sara-llm --max-model-len 4096 --gpu-memory-utilization 0.70 --enable-auto-tool-choice --tool-call-parser hermes --port 8001 2>&1 | tee /workspace/llm.log'

echo "Starting STT (Whisper large-v3) on :8002 ..."
NVLIBS=$(python -c "import nvidia,glob;base=list(nvidia.__path__)[0];print(':'.join(glob.glob(base+'/*/lib')))")
tmux kill-session -t stt 2>/dev/null
tmux new -s stt -d "cd /workspace && LD_LIBRARY_PATH=$NVLIBS uvicorn stt_server:app --host 0.0.0.0 --port 8002 2>&1 | tee /workspace/stt.log"

echo ""
echo "Two servers launching in tmux (llm, stt). TTS is Uplift AI (cloud, off-box)."
echo "Qwen-14B takes ~2-4 min to load. Watch:  tail -n 6 /workspace/llm.log"
echo "Then run the agent:  cd /workspace/Build3 && tmux new -s agent -d 'python agent.py dev 2>&1 | tee /workspace/agent.log'"
