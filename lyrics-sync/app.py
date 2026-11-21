from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from difflib import SequenceMatcher
import tempfile, os, re, uuid, threading, time, resource, platform, requests, logging

app = FastAPI(title="Auto Lyrics Sync API", version="1.3.0")
logger = logging.getLogger("lyrics_sync")

@app.middleware("http")
async def request_trace(request, call_next):
    started = time.time()
    if request.url.path == "/api/sync":
        logger.info("SYNC_UPLOAD_RECEIVED method=%s content_length=%s",
                    request.method, request.headers.get("content-length", "unknown"))
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("REQUEST_FAILED method=%s path=%s",
                         request.method, request.url.path)
        raise
    if request.url.path == "/api/sync":
        logger.info("SYNC_UPLOAD_RESPONSE status=%s elapsed_seconds=%.2f",
                    response.status_code, time.time() - started)
    return response
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

_model = None
_model_lock = threading.Lock()
_jobs = {}
_jobs_lock = threading.Lock()
_started_at = time.time()
MAX_AUDIO_BYTES = 40 * 1024 * 1024
MAX_LYRICS_CHARS = 30000
MAX_LYRIC_LINES = 500
MAX_ACTIVE_JOBS = 1
JOB_RETENTION_SECONDS = 2 * 60 * 60
ALLOWED_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".mp4"}

def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(os.getenv("WHISPER_MODEL", "tiny"), device="cpu", compute_type="int8", cpu_threads=1, num_workers=1)
    return _model

def transcribe_audio(path, language, lyrics):
    """Prefer hosted Groq Whisper so the small Render instance does not load a local model."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    provider = os.getenv("TRANSCRIPTION_PROVIDER", "groq" if api_key else "local").strip().lower()
    if provider == "groq":
        if not api_key:
            raise RuntimeError("Hosted AI is selected but GROQ_API_KEY is missing. Add it in Render Environment, or set TRANSCRIPTION_PROVIDER=local.")
        if os.path.getsize(path) > 25 * 1024 * 1024:
            raise ValueError("Hosted Groq transcription accepts files up to 25 MB on this API tier. Compress the audio or use a smaller file.")
        model_name = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
        # Send a short lyrics excerpt as vocabulary context; stay below Groq's 896-character limit.
        prompt_excerpt = lyrics.strip()[:800]
        with open(path, "rb") as audio_file:
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data=[("model", model_name), ("response_format", "verbose_json"), ("temperature", "0")]
                     + ([("language", language)] if language != "auto" else [])
                     + ([("prompt", prompt_excerpt)] if prompt_excerpt else [])
                     + [("timestamp_granularities[]", "word")],
                files={"file": (os.path.basename(path), audio_file, "application/octet-stream")},
                timeout=(20, 900),
            )
        if not response.ok:
            detail = response.text[:500]
            raise RuntimeError(f"Hosted transcription API returned HTTP {response.status_code}: {detail}")
        payload = response.json()
        remote_words = payload.get("words") or []
        words = []
        for item in remote_words:
            found = tokens(item.get("word", ""))
            if found and item.get("start") is not None and item.get("end") is not None:
                words.append({"token": found[0], "start": float(item["start"]), "end": float(item["end"])})
        if not words:
            raise RuntimeError("Hosted AI returned no word-level timestamps. Please retry or use local transcription.")
        return words, payload.get("text", ""), payload.get("language", language), float(payload.get("duration", 0) or 0)

    model = get_model()
    lang = None if language == "auto" else language
    segments, info = model.transcribe(
        path, language=lang, word_timestamps=True, vad_filter=True,
        beam_size=1, condition_on_previous_text=False
    )
    words, transcript = [], []
    for seg in segments:
        transcript.append(seg.text)
        if seg.words:
            for word in seg.words:
                found = tokens(word.word)
                if found:
                    words.append({"token": found[0], "start": float(word.start), "end": float(word.end)})
    return words, " ".join(transcript), info.language, float(info.duration or 0)

def tokens(text):
    return re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)

@app.get("/")
def health():
    return {"status": "ok", "service": "Auto Lyrics Sync API", "version": "1.3.0"}

@app.get("/api/diagnostics")
def diagnostics():
    try:
        peak_rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except Exception:
        peak_rss_mb = None
    key_present = bool(os.getenv("GROQ_API_KEY", "").strip())
    provider = os.getenv("TRANSCRIPTION_PROVIDER", "groq" if key_present else "local").strip().lower()
    return {
        "status": "ok", "version": "1.3.0", "provider": provider,
        "hosted_key_configured": key_present,
        "local_model_loaded": _model is not None,
        "uptime_seconds": int(time.time() - _started_at),
        "peak_rss_mb": peak_rss_mb,
        "platform": platform.platform(),
    }

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Sync job not found. The server may have restarted; please upload the audio again.")
        return dict(job)

def process_job(job_id, path, lyrics, language):
    try:
        with _jobs_lock:
            _jobs[job_id] = {"status": "processing", "message": "AI is analyzing the audio.", "updated_at": time.time()}
        # Serialize inference per instance; hosted transcription avoids loading Whisper into Render RAM.
        with _model_lock:
            words, transcript, detected_language, duration = transcribe_audio(path, language, lyrics)
        if not words:
            raise ValueError("Speech could not be detected. Try clearer audio or another language setting.")
        lyric_lines = [line.strip() for line in lyrics.splitlines() if line.strip()]
        aligned, cursor = [], 0
        for line in lyric_lines:
            target = tokens(line)
            if not target:
                continue
            best, best_score = None, 0.0
            for start in range(cursor, min(len(words), cursor + 120)):
                low = max(1, len(target) - 4)
                high = min(len(target) + 6, len(words) - start)
                for length in range(low, high + 1):
                    heard = [item["token"] for item in words[start:start + length]]
                    score = SequenceMatcher(None, target, heard).ratio()
                    if score > best_score:
                        best, best_score = (start, start + length - 1), score
            if best and best_score >= 0.30:
                first, last = best
                aligned.append({"text": line, "start": words[first]["start"], "end": words[last]["end"], "confidence": round(best_score, 2)})
                cursor = max(cursor, last + 1)
            else:
                aligned.append({"text": line, "start": None, "end": None, "confidence": 0})
        with _jobs_lock:
            _jobs[job_id] = {"status": "completed", "updated_at": time.time(), "result": {
                "language": detected_language, "duration": duration,
                "lines": aligned, "transcript": " ".join(transcript)
            }}
    except Exception as exc:
        message = str(exc).strip() or "Audio processing failed. Please try again."
        with _jobs_lock:
            _jobs[job_id] = {"status": "failed", "error": message, "updated_at": time.time()}
    finally:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass

@app.post("/api/sync")
async def sync(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    lyrics: str = Form(...),
    language: str = Form("auto"),
):
    if not lyrics.strip():
        raise HTTPException(400, "Paste the full lyrics first.")
    if len(lyrics) > MAX_LYRICS_CHARS:
        raise HTTPException(413, "Lyrics are too long. Please keep them under 30,000 characters.")
    lyric_line_count = sum(1 for line in lyrics.splitlines() if line.strip())
    if lyric_line_count > MAX_LYRIC_LINES:
        raise HTTPException(413, "Please keep lyrics under 500 non-empty lines for reliable processing.")
    if lyric_line_count == 0:
        raise HTTPException(400, "No readable lyric lines found. Paste the lyrics one line per row.")
    if language not in {"auto", "or", "hi", "en"}:
        raise HTTPException(400, "Choose Auto Detect, Odia, Hindi, or English.")
    suffix = os.path.splitext(audio.filename or "audio.mp3")[1].lower() or ".mp3"
    if suffix not in ALLOWED_AUDIO:
        raise HTTPException(415, "Unsupported audio format. Use MP3, WAV, M4A, AAC, OGG, FLAC, or WEBM.")
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            path = tmp.name
            total = 0
            while True:
                chunk = await audio.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > (25 * 1024 * 1024 if os.getenv("GROQ_API_KEY", "").strip() and os.getenv("TRANSCRIPTION_PROVIDER", "groq").strip().lower() == "groq" else MAX_AUDIO_BYTES):
                    raise HTTPException(413, "Audio file exceeds the current transcription provider limit (25 MB hosted / 40 MB local).")
                tmp.write(chunk)
        job_id = uuid.uuid4().hex
        with _jobs_lock:
            now = time.time()
            for old_id, old_job in list(_jobs.items()):
                if old_job.get("status") in {"completed", "failed"} and now - old_job.get("updated_at", now) > JOB_RETENTION_SECONDS:
                    _jobs.pop(old_id, None)
            active = sum(1 for item in _jobs.values() if item.get("status") in {"queued", "processing"})
            if active >= MAX_ACTIVE_JOBS:
                raise HTTPException(429, "Another audio is being processed. Please wait for it to finish, then try again.")
            _jobs[job_id] = {"status": "queued", "message": "Upload received. Waiting for AI processing.", "updated_at": now}
            if len(_jobs) > 50:
                for old_id, old_job in list(_jobs.items()):
                    if old_job.get("status") in {"completed", "failed"}:
                        _jobs.pop(old_id, None)
                        if len(_jobs) <= 40:
                            break
        background_tasks.add_task(process_job, job_id, path, lyrics, language)
        path = None
        return {"job_id": job_id, "status": "queued"}
    finally:
        await audio.close()
        if path and os.path.exists(path):
            os.unlink(path)
