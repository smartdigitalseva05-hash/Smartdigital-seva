"""Protected FastAPI wrapper for the Mithi v2 Flash TTS model.

The model files are downloaded separately; see README.md in this folder.
"""
from __future__ import annotations

import hmac
import io
import os
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import numpy as np
import soundfile as sf
import torch
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = Path(os.getenv("MITHI_MODEL_DIR", BASE_DIR / "mithi-v2-flash")).resolve()
API_TOKEN = os.getenv("VOICE_API_KEY", "")
SAMPLE_RATE = 24_000
MAX_TEXT_CHARS = 3_000
MODEL = None
MODEL_LOCK = threading.Lock()

LANGUAGES = {"hi", "or", "en", "bn", "gu", "kn", "ml", "mr", "pa", "ta", "te"}
VOICES = {
    "satvik", "anirban", "nakul", "vasant", "siddhant",
    "charvi", "ahana", "vaidehi", "malini", "jahnavi",
}


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    if not API_TOKEN:
        raise HTTPException(status_code=503, detail="Server owner must configure VOICE_API_KEY.")
    expected = f"Bearer {API_TOKEN}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global MODEL
    if not (MODEL_DIR / "run.py").is_file():
        raise RuntimeError(
            f"Mithi model not found at {MODEL_DIR}. Follow backend/README.md to download it."
        )
    torch.set_num_threads(max(1, int(os.getenv("TORCH_NUM_THREADS", "2"))))
    sys.path.insert(0, str(MODEL_DIR))
    from run import Mithi  # imported from the downloaded model directory

    MODEL = Mithi(device=os.getenv("MITHI_DEVICE", "cpu"))
    yield
    MODEL = None


app = FastAPI(title="AI Voice Studio Neural TTS", version="0.1.0", lifespan=lifespan)

origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "").split(",") if item.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    language: Literal["hi", "or", "en", "bn", "gu", "kn", "ml", "mr", "pa", "ta", "te"]
    voice: Literal[
        "satvik", "anirban", "nakul", "vasant", "siddhant",
        "charvi", "ahana", "vaidehi", "malini", "jahnavi",
    ] = "ahana"


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": MODEL is not None}


@app.post("/api/tts", dependencies=[Depends(require_api_token)])
def synthesize(request: SpeechRequest):
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Text cannot be blank.")
    if request.language not in LANGUAGES or request.voice not in VOICES:
        raise HTTPException(status_code=422, detail="Unsupported language or voice.")
    if MODEL is None:
        raise HTTPException(status_code=503, detail="TTS model is not ready.")

    try:
        # Serialize inference to avoid concurrent memory spikes on small CPU hosts.
        with MODEL_LOCK:
            audio = MODEL.synthesize(
                request.text.strip(),
                lang=request.language,
                voice=request.voice,
            )
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        audio = np.asarray(audio, dtype=np.float32).squeeze()
        if audio.size == 0:
            raise ValueError("The model returned empty audio.")
        buffer = io.BytesIO()
        sf.write(buffer, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
        return Response(
            content=buffer.getvalue(),
            media_type="audio/wav",
            headers={"Content-Disposition": 'attachment; filename="speech.wav"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Keep internal paths and stack traces out of public responses.
        raise HTTPException(status_code=500, detail="Speech generation failed.") from exc
