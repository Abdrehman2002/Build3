import io
import wave
import numpy as np
import torch
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
from snac import SNAC

MODEL_DIR = "/workspace/models/orpheus-hf"
DEVICE = "cuda"

print("Loading Orpheus model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.bfloat16).to(DEVICE).eval()
print("Loading SNAC decoder...")
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


def decode_audio(generated, input_len):
    row = generated[input_len:]
    row = row[row >= 128266]
    n = (row.shape[0] // 7) * 7
    if n == 0:
        return None
    codes = (row[:n] - 128266).tolist()
    l1, l2, l3 = [], [], []
    for i in range(n // 7):
        l1.append(codes[7 * i])
        l2.append(codes[7 * i + 1] - 4096)
        l3.append(codes[7 * i + 2] - 2 * 4096)
        l3.append(codes[7 * i + 3] - 3 * 4096)
        l2.append(codes[7 * i + 4] - 4 * 4096)
        l3.append(codes[7 * i + 5] - 5 * 4096)
        l3.append(codes[7 * i + 6] - 6 * 4096)
    c0 = torch.tensor(l1, device=DEVICE).unsqueeze(0)
    c1 = torch.tensor(l2, device=DEVICE).unsqueeze(0)
    c2 = torch.tensor(l3, device=DEVICE).unsqueeze(0)
    with torch.inference_mode():
        audio = snac.decode([c0, c1, c2])
    return audio.squeeze().detach().cpu().float().numpy()


def to_int16(audio):
    return (np.clip(audio, -1, 1) * 32767).astype(np.int16)


def to_wav(audio, sr=24000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(to_int16(audio).tobytes())
    return buf.getvalue()


@app.post("/v1/audio/speech")
def speech(req: SpeechReq):
    full = build_inputs(req.input)
    with torch.inference_mode():
        out = model.generate(
            input_ids=full,
            attention_mask=torch.ones_like(full),
            max_new_tokens=2000,
            do_sample=True,
            temperature=0.8,
            top_p=0.9,
            repetition_penalty=1.1,
            eos_token_id=128258,
        )
    audio = decode_audio(out[0], full.shape[1])
    if audio is None:
        return Response(content=b"no audio tokens", status_code=500)
    if req.response_format == "pcm":
        return Response(content=to_int16(audio).tobytes(), media_type="audio/pcm")
    return Response(content=to_wav(audio), media_type="audio/wav")
