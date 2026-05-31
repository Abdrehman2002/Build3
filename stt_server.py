import io
from fastapi import FastAPI, UploadFile, File, Form
from faster_whisper import WhisperModel

whisper = WhisperModel("/workspace/models/whisper", device="cuda", compute_type="float16")
app = FastAPI()


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form("whisper-1"),
    language: str = Form("ur"),
):
    data = await file.read()
    segments, info = whisper.transcribe(io.BytesIO(data), language=language)
    text = "".join(s.text for s in segments).strip()
    return {"text": text}
