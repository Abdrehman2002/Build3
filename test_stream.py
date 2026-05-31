"""Judge the streaming TTS (port 8004) with Whisper (port 8002).
If TRANSCRIBED matches INPUT, the streamed audio is clean (not garbled)."""
import sys
import requests

INPUT = "السلام علیکم، میں احمد ہوں، ڈائیوو ایکسپریس کی طرف سے۔ آپ کیسے ہیں؟"
PORT = sys.argv[1] if len(sys.argv) > 1 else "8004"

r = requests.post(
    f"http://localhost:{PORT}/v1/audio/speech",
    json={"input": INPUT, "response_format": "wav"},
    timeout=120,
)
open("/workspace/stream_out.wav", "wb").write(r.content)
print(f"wav bytes: {len(r.content)}  (http {r.status_code})")

with open("/workspace/stream_out.wav", "rb") as f:
    t = requests.post(
        "http://localhost:8002/v1/audio/transcriptions",
        files={"file": ("a.wav", f, "audio/wav")},
        data={"language": "ur"},
        timeout=120,
    )
print("INPUT      :", INPUT)
print("TRANSCRIBED:", t.json().get("text"))
