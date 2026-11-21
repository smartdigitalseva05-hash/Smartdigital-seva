from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from difflib import SequenceMatcher
import tempfile, os, re, uuid, threading, traceback

app = FastAPI(title="Auto Lyrics Sync API", version="1.1.0")
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
MAX_AUDIO_BYTES = 40 * 1024 * 1024
MAX_LYRICS_CHARS = 30000
ALLOWED_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".mp4"}

def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(os.getenv("WHISPER_MODEL", "tiny"), device="cpu", compute_type="int8")
    return _model

def tokens(text):
    return re.findall(r"[^\\W_]+", text.lower(), flags=re.UNICODE)

@app.get("/")
def health():
    return {"status": "ok", "service": "Auto Lyrics Sync API", "version": "1.1.0"}

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Sync job not found. Please upload the audio again.")
        return dict(job)

def process_job(job_id, path, lyrics, language):
    try:
        with _jobs_lock:
            _jobs[job_id] = {"status": "processing", "message": "AI is analyzing the audio."}
        # Keep model inference off the web event loop and serialize model use on small hosts.
        with _model_lock:
            model = get_model()
            lang = None if language == "auto" else language
            segments, info = model.transcribe(
                path, language=lang, word_timestamps=True, vad_filter=True, beam_size=3
            )
            words, transcript = [], []
            for seg in segments:
                transcript.append(seg.text)
                if seg.words:
                    for word in seg.words:
                        found = tokens(word.word)
                        if found:
                            words.append({"token": found[0], "start": float(word.start), "end": float(word.end)})
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
            _jobs[job_id] = {"status": "completed", "result": {
                "language": info.language, "duration": info.duration,
                "lines": aligned, "transcript": " ".join(transcript)
            }}
    except Exception as exc:
        message = str(exc).strip() or "Audio processing failed. Please try again."
        with _jobs_lock:
            _jobs[job_id] = {"status": "failed", "error": message}
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
                if total > MAX_AUDIO_BYTES:
                    raise HTTPException(413, "Audio file must be 40 MB or smaller.")
                tmp.write(chunk)
        job_id = uuid.uuid4().hex
        with _jobs_lock:
            _jobs[job_id] = {"status": "queued", "message": "Upload received. Waiting for AI processing."}
            # Bound memory use on the free instance.
            if len(_jobs) > 30:
                for old_id in list(_jobs)[:-20]:
                    _jobs.pop(old_id, None)
        background_tasks.add_task(process_job, job_id, path, lyrics, language)
        path = None
        return {"job_id": job_id, "status": "queued"}
    finally:
        await audio.close()
        if path and os.path.exists(path):
            os.unlink(path)
