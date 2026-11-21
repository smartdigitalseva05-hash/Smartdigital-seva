from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from difflib import SequenceMatcher
import tempfile, os, re, uuid, threading, time, resource, platform, requests, logging, unicodedata

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
            raise RuntimeError("Hosted AI ବାଛାଯାଇଛି, କିନ୍ତୁ GROQ_API_KEY ମିଳିଲା ନାହିଁ। Render Environment ରେ ଏହା ଯୋଡ଼ନ୍ତୁ।")
        if os.path.getsize(path) > 25 * 1024 * 1024:
            raise ValueError("ଏହି Groq API ରେ ୨୫ MB ପର୍ଯ୍ୟନ୍ତ ଅଡିଓ ଗ୍ରହଣ ହୁଏ। ଅଡିଓକୁ ଛୋଟ କରନ୍ତୁ କିମ୍ବା ଅନ୍ୟ ଫାଇଲ୍ ବାଛନ୍ତୁ।")
        model_name = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
        # Do not send Odia lyrics as the Whisper prompt: Unicode UTF-8 byte length
        # can exceed Groq's 896-character prompt limit even after slicing Python chars.
        # Full lyrics remain available below for timestamp alignment after transcription.
        with open(path, "rb") as audio_file:
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data=[("model", model_name), ("response_format", "verbose_json"), ("temperature", "0")]
                     # Groq Whisper does not list Odia (or) as a supported forced-language value.
                     # Omit it for Odia so Whisper can detect the spoken language automatically.
                     + ([("language", language)] if language not in {"auto", "or"} else [])
                     + [("timestamp_granularities[]", "word")],
                files={"file": (os.path.basename(path), audio_file, "application/octet-stream")},
                timeout=(20, 900),
            )
        if not response.ok:
            detail = response.text[:500]
            raise RuntimeError(f"Hosted AI ଟ୍ରାନ୍ସକ୍ରିପ୍ସନ୍ API ରୁ HTTP {response.status_code}: {detail}")
        payload = response.json()
        remote_words = payload.get("words") or []
        words = []
        for item in remote_words:
            if item.get("start") is not None and item.get("end") is not None:
                words.extend(timed_tokens(item.get("word", ""), item["start"], item["end"]))
        if not words:
            raise RuntimeError("Hosted AI ଶବ୍ଦ ଅନୁଯାୟୀ ସମୟ ଦେଇନାହିଁ। ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।")
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
                words.extend(timed_tokens(word.word, word.start, word.end))
    return words, " ".join(transcript), info.language, float(info.duration or 0)

def tokens(text):
    """Tokenize Unicode words without splitting Indic-script combining marks."""
    text = unicodedata.normalize("NFC", str(text or "")).casefold()
    result, current = [], []
    for char in text:
        category = unicodedata.category(char)
        if category.startswith("L") or category.startswith("M"):
            current.append(char)
        elif current:
            result.append("".join(current))
            current = []
    if current:
        result.append("".join(current))
    return result


def timed_tokens(text, start, end):
    """Preserve all Unicode tokens when an ASR timestamp contains multiple words."""
    parts = tokens(text)
    if not parts:
        return []
    start, end = float(start), float(end)
    span = max(0.0, end - start)
    count = len(parts)
    return [
        {"token": part,
         "start": start + span * index / count,
         "end": start + span * (index + 1) / count}
        for index, part in enumerate(parts)
    ]


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
            raise HTTPException(404, "Sync କାମ ମିଳିଲା ନାହିଁ। ସର୍ଭର ପୁନଃଚାଳୁ ହୋଇଥାଇପାରେ; ଅଡିଓ ପୁଣି ଅପଲୋଡ୍ କରନ୍ତୁ।")
        return dict(job)

def process_job(job_id, path, lyrics, language):
    try:
        with _jobs_lock:
            _jobs[job_id] = {"status": "processing", "message": "AI ଅଡିଓ ବିଶ୍ଳେଷଣ କରୁଛି।", "updated_at": time.time()}
        # Serialize inference per instance; hosted transcription avoids loading Whisper into Render RAM.
        with _model_lock:
            words, transcript, detected_language, duration = transcribe_audio(path, language, lyrics)
        if not words:
            raise ValueError("ଅଡିଓରେ କଥା/ଗୀତ ଚିହ୍ନଟ ହୋଇନାହିଁ। ସ୍ପଷ୍ଟ ଅଡିଓ କିମ୍ବା ଅନ୍ୟ ଭାଷା ବାଛନ୍ତୁ।")
        lyric_lines = [line.strip() for line in lyrics.splitlines() if line.strip()]
        aligned, cursor = [], 0
        for line in lyric_lines:
            target = tokens(line)
            if not target:
                continue
            best, best_score = None, 0.0
            for start in range(cursor, min(len(words), cursor + 120)):
                tolerance = max(4, int(len(target) * 0.5))
                low = max(1, len(target) - tolerance)
                high = min(len(target) + tolerance, len(words) - start)
                for length in range(low, high + 1):
                    heard = [item["token"] for item in words[start:start + length]]
                    score = SequenceMatcher(None, target, heard).ratio()
                    if score > best_score:
                        best, best_score = (start, start + length - 1), score
            minimum_score = 0.42 if len(target) >= 4 else 0.55
            if best and best_score >= minimum_score:
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
        message = str(exc).strip() or "ଅଡିଓ ପ୍ରକ୍ରିୟା ବିଫଳ ହେଲା। ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।"
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
        raise HTTPException(400, "ପ୍ରଥମେ ସମ୍ପୂର୍ଣ୍ଣ ଗୀତିକା ଲେଖନ୍ତୁ।")
    if len(lyrics) > MAX_LYRICS_CHARS:
        raise HTTPException(413, "ଗୀତିକା ବହୁତ ଲମ୍ବା। ୩୦,୦୦୦ ଅକ୍ଷର ମଧ୍ୟରେ ରଖନ୍ତୁ।")
    lyric_line_count = sum(1 for line in lyrics.splitlines() if line.strip())
    if lyric_line_count > MAX_LYRIC_LINES:
        raise HTTPException(413, "ଭଲ ଭାବେ ପ୍ରକ୍ରିୟା ପାଇଁ ୫୦୦ ରୁ କମ୍ ଖାଲି ନଥିବା ଧାଡ଼ି ରଖନ୍ତୁ।")
    if lyric_line_count == 0:
        raise HTTPException(400, "ପଢ଼ିହେବା ଭଳି ଗୀତିକା ଧାଡ଼ି ମିଳିଲା ନାହିଁ। ପ୍ରତ୍ୟେକ ଧାଡ଼ିକୁ ଅଲଗା ଲାଇନ୍‌ରେ ଲେଖନ୍ତୁ।")
    if language not in {"auto", "or", "hi", "en"}:
        raise HTTPException(400, "ସ୍ୱୟଂଚାଳିତ ଚିହ୍ନଟ, ଓଡ଼ିଆ, ହିନ୍ଦୀ କିମ୍ବା ଇଂରାଜୀ ବାଛନ୍ତୁ।")
    suffix = os.path.splitext(audio.filename or "audio.mp3")[1].lower() or ".mp3"
    if suffix not in ALLOWED_AUDIO:
        raise HTTPException(415, "ଏହି ଅଡିଓ ଫର୍ମାଟ୍ ସମର୍ଥିତ ନୁହେଁ। MP3, WAV, M4A, AAC, OGG, FLAC କିମ୍ବା WEBM ବ୍ୟବହାର କରନ୍ତୁ।")
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
                    raise HTTPException(413, "ଅଡିଓ ଫାଇଲ୍ ବର୍ତ୍ତମାନର ସୀମାଠାରୁ ବଡ଼ (Hosted ୨୫ MB / Local ୪୦ MB)।")
                tmp.write(chunk)
        job_id = uuid.uuid4().hex
        with _jobs_lock:
            now = time.time()
            for old_id, old_job in list(_jobs.items()):
                if old_job.get("status") in {"completed", "failed"} and now - old_job.get("updated_at", now) > JOB_RETENTION_SECONDS:
                    _jobs.pop(old_id, None)
            active = sum(1 for item in _jobs.values() if item.get("status") in {"queued", "processing"})
            if active >= MAX_ACTIVE_JOBS:
                raise HTTPException(429, "ଅନ୍ୟ ଏକ ଅଡିଓ ପ୍ରକ୍ରିୟା ଚାଲିଛି। ଏହା ସରିବା ପରେ ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।")
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
