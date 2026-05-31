"""Sweep streaming window/emit configs (seeded -> same tokens) and let Whisper judge each."""
import requests

INPUT = "السلام علیکم، میں احمد ہوں، ڈائیوو ایکسپریس کی طرف سے۔ آپ کیسے ہیں؟"
CONFIGS = [(4, 1), (4, 2), (8, 3), (8, 4), (12, 5), (16, 7)]

print("INPUT:", INPUT)
print("-" * 60)
for window, emit in CONFIGS:
    r = requests.post(
        "http://localhost:8004/v1/audio/speech",
        json={"input": INPUT, "response_format": "wav", "window": window, "emit": emit},
        timeout=180,
    )
    open("/workspace/sw.wav", "wb").write(r.content)
    with open("/workspace/sw.wav", "rb") as f:
        t = requests.post(
            "http://localhost:8002/v1/audio/transcriptions",
            files={"file": ("a.wav", f, "audio/wav")},
            data={"language": "ur"},
            timeout=120,
        )
    print(f"window={window:2d} emit={emit}  bytes={len(r.content):6d}  =>  {t.json().get('text')}")
