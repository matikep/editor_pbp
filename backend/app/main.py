import json
import os
import shutil
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .censor import censor_audio
from .transcribe import transcribe_audio

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Editor PBP - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def session_dir(session_id: str) -> Path:
    d = SESSIONS_DIR / session_id
    if not d.exists():
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    return d


# Las transcripciones corren de a una para no agotar la RAM
transcribe_lock = threading.Lock()


def write_status(d: Path, **status):
    tmp = d / "status.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False)
    tmp.replace(d / "status.json")


def run_transcription(session_id: str, audio_path: Path):
    d = SESSIONS_DIR / session_id
    try:
        with transcribe_lock:
            write_status(d, state="processing", progress=0.0)

            def on_progress(p: float):
                write_status(d, state="processing", progress=round(p, 4))

            result = transcribe_audio(str(audio_path), on_progress)

        result["id"] = session_id
        with open(d / "transcript.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        write_status(d, state="done", progress=1.0)
    except Exception as e:
        write_status(d, state="error", error=str(e))


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    d = SESSIONS_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "audio").suffix or ".wav"
    audio_path = d / f"audio{ext}"
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    write_status(d, state="queued", progress=0.0)
    threading.Thread(
        target=run_transcription, args=(session_id, audio_path), daemon=True
    ).start()

    return {"id": session_id, "state": "queued"}


@app.get("/transcribe/status/{session_id}")
async def transcribe_status(session_id: str):
    d = session_dir(session_id)
    status_path = d / "status.json"
    if not status_path.exists():
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    with open(status_path, encoding="utf-8") as f:
        return json.load(f)


class CensorRange(BaseModel):
    start: float
    end: float


class CensorRequest(BaseModel):
    id: str
    ranges: list[CensorRange]
    mode: str = "beep"


@app.post("/censor")
async def censor(req: CensorRequest):
    d = session_dir(req.id)
    audio_files = [p for p in d.glob("audio.*")]
    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio original no encontrado")
    audio_path = audio_files[0]

    if req.mode not in ("beep", "silence"):
        raise HTTPException(status_code=400, detail="mode debe ser 'beep' o 'silence'")

    ranges = [r.model_dump() for r in req.ranges]
    result_audio = censor_audio(str(audio_path), ranges, mode=req.mode)

    out_path = d / "censored.wav"
    result_audio.export(out_path, format="wav")

    return FileResponse(out_path, media_type="audio/wav", filename="audio_censurado.wav")


@app.get("/transcript/export/{session_id}")
async def export_transcript(session_id: str, fmt: str = "json"):
    d = session_dir(session_id)
    transcript_path = d / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcripcion no encontrada")

    if fmt == "json":
        return FileResponse(
            transcript_path, media_type="application/json", filename="transcripcion.json"
        )

    if fmt == "txt":
        with open(transcript_path, encoding="utf-8") as f:
            data = json.load(f)
        text = "\n".join(seg["text"] for seg in data["segments"])
        txt_path = d / "transcripcion.txt"
        txt_path.write_text(text, encoding="utf-8")
        return FileResponse(txt_path, media_type="text/plain", filename="transcripcion.txt")

    raise HTTPException(status_code=400, detail="fmt debe ser 'json' o 'txt'")


@app.get("/transcript/{session_id}")
async def get_transcript(session_id: str):
    d = session_dir(session_id)
    transcript_path = d / "transcript.json"
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcripcion no encontrada")
    with open(transcript_path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/health")
async def health():
    return {"status": "ok"}
