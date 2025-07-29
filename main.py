from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import tempfile
import os
from pathlib import Path
import whisper

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "ok"}

model = whisper.load_model("base")

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    wav_path = tmp_path
    if suffix != ".wav":
        wav_path = f"{tmp_path}.wav"
        cmd = [
            "ffmpeg", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-y", wav_path,
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            os.remove(tmp_path)
            raise HTTPException(status_code=400, detail="FFmpeg conversion failed")

    result = model.transcribe(wav_path)

    os.remove(tmp_path)
    if wav_path != tmp_path and os.path.exists(wav_path):
        os.remove(wav_path)

    return {"text": result.get("text", "").strip()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
