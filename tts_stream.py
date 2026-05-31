"""Experimental STREAMING Orpheus server (port 8004).
Canonical sliding-window SNAC decode: constant-time per chunk, stable/contiguous.
Tunable via WINDOW_FRAMES / EMIT_IDX so we can dial in correct audio."""
import io
import wave
import threading
import queue
import numpy as np
import torch
from fastapi import FastAPI
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from snac import SNAC

MODEL_DIR = "/workspace/models/orpheus-hf"
DEVICE = "cuda"

# --- tunables for getting the stream right ---
WINDOW_FRAMES = 4      # frames decoded per chunk (context window)
EMIT_IDX = 1           # which frame of the window to emit (0-based)
FRAME_SAMPLES = 2048   # SNAC-24kHz samples per frame
# ---------------------------------------------

print("Loading Orpheus...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.bfloat16).to(DEVICE).eval()
snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").to(DEVICE).eval()
print("Ready.")

app = FastAPI()


class SpeechReq(BaseModel):
    input: str
    voice: str = ""
    model: str = "orpheus"
    response_format: str = "wav"


def build_inputs(text):
    ids = tokenizer(text, return_tensors="pt").input_ids
    start = torch.tensor([[128259]], dtype=torch.int64)
    end = torch.tensor([[128009, 128260]], dtype=torch.int64)
    return torch.cat([start, ids, end], dim=1).to(DEVICE)


class TokenStreamer:
    def __init__(self):
        self.q = queue.Queue()
        self._first = True

    def put(self, value):
        if self._first:
            self._first = False
            return
        for t in value.view(-1).tolist():
            self.q.put(int(t))

    def end(self):
        self.q.put(None)


def decode_window(window_codes):
    n = len(window_codes) // 7
    c0, c1, c2 = [], [], []
    for j in range(n):
        i = 7 * j
        c0.append(window_codes[i])
        c1.append(window_codes[i + 1]); c1.append(window_codes[i + 4])
        c2.append(window_codes[i + 2]); c2.append(window_codes[i + 3])
        c2.append(window_codes[i + 5]); c2.append(window_codes[i + 6])
    t0 = torch.tensor([c0], device=DEVICE, dtype=torch.int32)
    t1 = torch.tensor([c1], device=DEVICE, dtype=torch.int32)
    t2 = torch.tensor([c2], device=DEVICE, dtype=torch.int32)
    for c in (t0, t1, t2):
        if int(c.min()) < 0 or int(c.max()) > 4096:
            return None
    with torch.inference_mode():
        audio = snac.decode([t0, t1, t2])
    return audio.squeeze().detach().cpu().float().numpy()


def stream_pcm(text):
    inputs = build_inputs(text)
    streamer = TokenStreamer()
    kwargs = dict(
        input_ids=inputs, attention_mask=torch.ones_like(inputs), max_new_tokens=2000,
        do_sample=True, temperature=0.8, top_p=0.9, repetition_penalty=1.1,
        eos_token_id=128258, streamer=streamer,
    )
    threading.Thread(target=lambda: model.generate(**kwargs), daemon=True).start()
    win = WINDOW_FRAMES * 7
    index = 0
    buf = []
    while True:
        t = streamer.q.get()
        if t is None:
            break
        if t < 128266:
            continue
        code = t - 128266 - ((index % 7) * 4096)
        if code <= 0:
            continue
        buf.append(code)
        index += 1
        if index % 7 == 0 and len(buf) >= win:
            audio = decode_window(buf[-win:])
            if audio is not None:
                s = EMIT_IDX * FRAME_SAMPLES
                chunk = audio[s:s + FRAME_SAMPLES]
                yield (np.clip(chunk, -1, 1) * 32767).astype(np.int16).tobytes()


@app.post("/v1/audio/speech")
def speech(req: SpeechReq):
    if req.response_format == "pcm":
        return StreamingResponse(stream_pcm(req.input), media_type="audio/pcm")
    data = b"".join(stream_pcm(req.input))
    if not data:
        return Response(content=b"no audio", status_code=500)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(data)
    return Response(content=buf.getvalue(), media_type="audio/wav")
