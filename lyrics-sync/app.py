from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from difflib import SequenceMatcher
import tempfile, os, re, uuid, threading, time, resource, platform, requests, logging
from lyrics_core import (
    tokens, timed_tokens, validate_lyrics, validate_audio_size,
    select_transcription_provider, parse_allowed_origins, active_job_count,
)

app = FastAPI(title="Auto Lyrics Sync API", version="1.6.4")
logger = logging.getLogger("lyrics_sync")

@app.middleware("http")
async def request_trace(request, call_next):
    started = time.time()
    if request.url.path.startswith("/api/"):
        logger.info("API_REQUEST method=%s path=%s origin=%s content_length=%s",
                    request.method, request.url.path,
                    request.headers.get("origin", "-"),
                    request.headers.get("content-length", "unknown"))
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("REQUEST_FAILED method=%s path=%s",
                         request.method, request.url.path)
        raise
    if request.url.path.startswith("/api/"):
        logger.info("API_RESPONSE method=%s path=%s status=%s elapsed_seconds=%.2f",
                    request.method, request.url.path, response.status_code,
                    time.time() - started)
    return response

allowed_origins = parse_allowed_origins(os.getenv("CORS_ALLOWED_ORIGINS"))
if not allowed_origins:
    logger.warning("CORS_ALLOWED_ORIGINS has no valid entries; browser cross-origin access is disabled.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    allow_credentials=False,
    max_age=600,
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
BUSY_JOB_MESSAGE = "ଅନ୍ୟ ଏକ ଅଡିଓ ପ୍ରକ୍ରିୟା ଚାଲିଛି। ଏହା ସରିବା ପରେ ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।"
ALLOWED_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".mp4"}

def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(os.getenv("WHISPER_MODEL", "tiny"), device="cpu", compute_type="int8", cpu_threads=1, num_workers=1)
    return _model

def transcribe_sarvam_batch(path, language, lyrics):
    """Transcribe long audio with Saaras v4 Batch API (phrase timestamps)."""
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Sarvam API Key ମିଳିଲା ନାହିଁ। Render Environment ରେ SARVAM_API_KEY ଯୋଡ଼ନ୍ତୁ।")

    headers = {"api-subscription-key": api_key, "Content-Type": "application/json"}
    base = "https://api.sarvam.ai/speech-to-text/job/v1"
    filename = "lyrics_sync_audio" + (os.path.splitext(path)[1].lower() or ".mp3")
    language_codes = {"or": "od-IN", "hi": "hi-IN", "en": "en-IN", "auto": "unknown"}
    language_code = language_codes.get(language, "unknown")

    def check(response, step):
        if not response.ok:
            try:
                detail = response.json()
            except Exception:
                detail = response.text[:400]
            raise RuntimeError(f"Sarvam {step} ବିଫଳ (HTTP {response.status_code}): {str(detail)[:500]}")
        return response.json() if response.content else {}

    # Bias Saaras toward the actual Odia words supplied by the user.
    # Saaras v4 accepts up to 50 keyterms, each up to 64 characters.
    keyterms = []
    seen_terms = set()
    for token in tokens(lyrics):
        if len(token) <= 64 and token not in seen_terms:
            seen_terms.add(token)
            keyterms.append(token)
        if len(keyterms) >= 50:
            break

    init = check(requests.post(
        base, headers=headers,
        json={"job_parameters": {
            "model": "saaras:v4", "mode": "transcribe",
            "language_code": language_code,
            "with_timestamps": True,
            "keyterms": keyterms,
            "with_diarization": True, "with_timestamps": True, "num_speakers": 1
        }},
        timeout=(20, 60)
    ), "job creation")
    job_id = init.get("job_id")
    if not job_id:
        raise RuntimeError("Sarvam batch job ID ଦେଇନାହିଁ।")

    links = check(requests.post(
        base + "/upload-files", headers=headers,
        json={"job_id": job_id, "files": [filename]}, timeout=(20, 60)
    ), "upload link")
    upload_item = (links.get("upload_urls") or {}).get(filename) or {}
    upload_url = upload_item.get("file_url") or upload_item.get("url")
    if not upload_url:
        raise RuntimeError("Sarvam ଅଡିଓ upload URL ଦେଇନାହିଁ।")
    with open(path, "rb") as audio_file:
        uploaded = requests.put(
            upload_url, data=audio_file,
            headers={"Content-Type": "application/octet-stream", "x-ms-blob-type": "BlockBlob"},
            timeout=(30, 900)
        )
    if not uploaded.ok:
        raise RuntimeError(f"Sarvam audio upload ବିଫଳ (HTTP {uploaded.status_code})।")

    check(requests.post(base + f"/{job_id}/start", headers=headers, json={}, timeout=(20, 60)), "job start")
    deadline = time.time() + 1500
    status = {}
    while time.time() < deadline:
        time.sleep(5)
        status = check(requests.get(base + f"/{job_id}/status", headers=headers, timeout=(20, 60)), "job status")
        state = str(status.get("job_state", "")).lower()
        if state in {"completed", "partiallycompleted"}:
            break
        if state == "failed":
            raise RuntimeError("Sarvam batch job ବିଫଳ: " + str(status.get("error_message") or "ଅଜଣା ତ୍ରୁଟି"))
    else:
        raise RuntimeError("Sarvam batch processing ୨୫ ମିନିଟ୍ ମଧ୍ୟରେ ସମ୍ପୂର୍ଣ୍ଣ ହେଲା ନାହିଁ।")

    details = status.get("job_details") or []
    output_names = [
        output.get("file_name")
        for item in details if str(item.get("state", "")).lower() == "success"
        for output in (item.get("outputs") or []) if output.get("file_name")
    ]
    if not output_names:
        raise RuntimeError("Sarvam transcript output file ମିଳିଲା ନାହିଁ।")
    downloads = check(requests.post(
        base + "/download-files", headers=headers,
        json={"job_id": job_id, "files": output_names}, timeout=(20, 60)
    ), "download link")
    download_map = downloads.get("download_urls") or {}
    output_payload = None
    for output_name in output_names:
        item = download_map.get(output_name) or {}
        download_url = item.get("file_url") or item.get("url")
        if download_url:
            result = requests.get(download_url, timeout=(20, 120))
            if result.ok:
                output_payload = result.json()
                break
    if output_payload is None:
        raise RuntimeError("Sarvam transcript ଡାଉନଲୋଡ୍ ହୋଇପାରିଲା ନାହିଁ।")

    # Sarvam Batch schemas vary: normalize every supported phrase-timing shape.
    payload = output_payload
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        payload = payload["result"]
    transcript = str(payload.get("transcript") or "") if isinstance(payload, dict) else ""
    words = []
    phrase_texts = []
    seen_phrases = set()

    def add_timed_phrase(text_value, start_value, end_value):
        if text_value is None or start_value is None or end_value is None:
            return
        try:
            start_value, end_value = float(start_value), float(end_value)
            if start_value < 0 or end_value <= start_value:
                return
        except (TypeError, ValueError):
            return
        phrase = str(text_value).strip()
        key = (phrase, round(start_value, 3), round(end_value, 3))
        if not phrase or key in seen_phrases:
            return
        seen_phrases.add(key)
        phrase_texts.append(phrase)
        words.extend(timed_tokens(phrase, start_value, end_value))

    def scan_timing_node(node):
        if isinstance(node, list):
            for child in node:
                scan_timing_node(child)
            return
        if not isinstance(node, dict):
            return

        # Entry-style timestamps, including nested diarization segments.
        text_value = (node.get("transcript") or node.get("text") or
                      node.get("word") or node.get("phrase") or node.get("chunk"))
        start_value = node.get("start_time_seconds", node.get("start", node.get("start_time")))
        end_value = node.get("end_time_seconds", node.get("end", node.get("end_time")))
        if text_value is not None and start_value is not None and end_value is not None:
            add_timed_phrase(text_value, start_value, end_value)

        # Sarvam's documented parallel arrays: words + start/end seconds.
        starts = node.get("start_time_seconds") or node.get("start") or node.get("starts") or []
        ends = node.get("end_time_seconds") or node.get("end") or node.get("ends") or []
        phrases = (node.get("words") or node.get("chunks") or
                   node.get("segments") or node.get("texts") or [])
        if isinstance(phrases, list) and isinstance(starts, list) and isinstance(ends, list):
            for index, phrase in enumerate(phrases):
                if index < len(starts) and index < len(ends):
                    add_timed_phrase(phrase, starts[index], ends[index])

        # Continue recursively: some batch output revisions wrap results in
        # data/output/transcription objects rather than exposing timestamps at root.
        for value in node.values():
            if isinstance(value, (dict, list)):
                scan_timing_node(value)

    # Scan the complete downloaded response, not only the optional `result` wrapper.
    # Sarvam batch output can place transcript/timestamps at the root while a
    # nested result object contains only metadata (or vice versa).
    scan_timing_node(output_payload)
    if not transcript and phrase_texts:
        transcript = " ".join(phrase_texts)
    if words:
        words.sort(key=lambda item: (item["start"], item["end"]))
    if not transcript:
        transcript = " ".join(phrase_texts)
    if not words:
        # Keep diagnostics safe for every provider response shape. These fields
        # are optional in Sarvam output and must never mask the real STT error.
        root_payload = output_payload if isinstance(output_payload, dict) else {}
        timestamps = payload.get("timestamps") if isinstance(payload, dict) else None
        diarized = payload.get("diarized_transcript") if isinstance(payload, dict) else None
        top_level_keys = list(payload.keys()) if isinstance(payload, dict) else [type(payload).__name__]
        timestamp_shape = (
            {key: type(value).__name__ for key, value in timestamps.items()}
            if isinstance(timestamps, dict) else type(timestamps).__name__
        )
        logger.error(
            "SARVAM_TIMING_MISSING top_level_keys=%s timestamp_shape=%s diarized_shape=%s",
            top_level_keys, timestamp_shape, type(diarized).__name__,
        )
        raise RuntimeError(
            "Sarvam transcript ମିଳିଛି, କିନ୍ତୁ ଏହି output ରେ ବ୍ୟବହାରଯୋଗ୍ୟ phrase timing ନାହିଁ।"
        )
    root_payload = output_payload if isinstance(output_payload, dict) else {}
    detected = (payload.get("language_code") if isinstance(payload, dict) else None) or root_payload.get("language_code") or language_code
    detected = {"od-IN": "or", "or-IN": "or", "hi-IN": "hi", "en-IN": "en"}.get(detected, detected)
    duration = max((item["end"] for item in words), default=0.0)
    return words, transcript, detected, float(duration)


def transcribe_audio(path, language, lyrics):
    """Use Odia-capable Saaras v4 exclusively for Odia; never silently fall back to English-biased Whisper."""
    sarvam_key = os.getenv("SARVAM_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    # Groq Whisper's language handling caused Odia devotional audio to be
    # mislabeled as English. That produces zero true matches and fake full-song
    # estimates, so Odia must stay on Saaras v4 with od-IN.
    if language == "or":
        if not sarvam_key:
            raise RuntimeError(
                "Odia sync needs SARVAM_API_KEY on Render. Groq fallback is disabled "
                "because it can misidentify Odia songs as English."
            )
        try:
            result = transcribe_sarvam_batch(path, language, lyrics)
        except Exception as exc:
            raise RuntimeError(
                "Odia AI transcription failed in Sarvam Saaras v4; no estimated timing was created. "
                + str(exc)
            ) from exc
        words, transcript, detected, duration = result
        if detected not in {"or", "od-IN", "or-IN"}:
            raise RuntimeError(
                "AI did not confirm Odia audio (detected: " + str(detected) +
                "). Please check the audio language and try again."
            )
        return words, transcript, "or", duration

    # Keep provider selection consistent with diagnostics and upload limits.
    provider = select_transcription_provider(
        language,
        os.getenv("TRANSCRIPTION_PROVIDER", "auto"),
        bool(sarvam_key),
        bool(groq_key),
    )
    if provider == "sarvam":
        return transcribe_sarvam_batch(path, language, lyrics)
    api_key = groq_key
    if provider == "groq":
        if not api_key:
            raise RuntimeError("Hosted AI is selected, but GROQ_API_KEY is missing from Render Environment.")
        if os.path.getsize(path) > 25 * 1024 * 1024:
            raise ValueError("Groq accepts audio files up to 25 MB. Reduce the audio size or choose another file.")
        model_name = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3")
        with open(path, "rb") as audio_file:
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data=[("model", model_name), ("response_format", "verbose_json"), ("temperature", "0")]
                     + ([("language", language)] if language not in {"auto"} else [])
                     + [("timestamp_granularities[]", "word")],
                files={"file": (os.path.basename(path), audio_file, "application/octet-stream")},
                timeout=(20, 900),
            )
        if not response.ok:
            raise RuntimeError(f"Hosted AI transcription API returned HTTP {response.status_code}: {response.text[:500]}")
        payload = response.json()
        remote_words = payload.get("words") or []
        words = []
        for item in remote_words:
            if item.get("start") is not None and item.get("end") is not None:
                words.extend(timed_tokens(item.get("word", ""), item["start"], item["end"]))
        if not words:
            raise RuntimeError("Hosted AI did not return word-level timestamps. Please try again.")
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



@app.get("/")
def health():
    return {"status": "ok", "service": "Auto Lyrics Sync API", "version": "1.6.4"}

@app.get("/api/diagnostics")
def diagnostics():
    try:
        peak_rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except Exception:
        peak_rss_mb = None
    sarvam_present = bool(os.getenv("SARVAM_API_KEY", "").strip())
    groq_present = bool(os.getenv("GROQ_API_KEY", "").strip())
    # Odia is deliberately pinned to Sarvam Saaras v4 regardless of the
    # generic provider preference; other languages follow TRANSCRIPTION_PROVIDER.
    configured_provider = os.getenv("TRANSCRIPTION_PROVIDER", "auto").strip().lower()
    if sarvam_present:
        odia_provider = "sarvam"
    else:
        odia_provider = "unavailable"
    provider = select_transcription_provider(
        "auto", configured_provider, sarvam_present, groq_present
    )
    return {
        "status": "ok", "version": "1.6.4", "provider": provider,
        "odia_provider": odia_provider,
        "hosted_key_configured": sarvam_present or groq_present,
        "sarvam_key_configured": sarvam_present,
        "groq_key_configured": groq_present,
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
                # Keep candidate windows close to the lyric length. Very wide windows
                # can accidentally match unrelated words in songs with repeated phrases.
                tolerance = max(2, int(len(target) * 0.3))
                low = max(1, len(target) - tolerance)
                high = min(len(target) + tolerance, len(words) - start)
                for length in range(low, high + 1):
                    heard = [item["token"] for item in words[start:start + length]]
                    # Require substantial token coverage as well as sequence similarity.
                    coverage = len(set(target) & set(heard)) / max(1, len(set(target)))
                    score = SequenceMatcher(None, target, heard, autojunk=False).ratio()
                    combined = score * 0.75 + coverage * 0.25
                    if combined > best_score:
                        best, best_score = (start, start + length - 1), combined
            # Conservative thresholds: a missed line is safer than a fabricated timestamp.
            minimum_score = 0.76 if len(target) >= 4 else 0.88
            if best and best_score >= minimum_score:
                first, last = best
                start_time = float(words[first]["start"])
                end_time = float(words[last]["end"])
                if (0 <= start_time < end_time and
                        (not duration or end_time <= duration + 1.0)):
                    aligned.append({"text": line, "start": round(start_time, 3), "end": round(end_time, 3), "confidence": round(best_score, 2)})
                    cursor = max(cursor, last + 1)
                else:
                    aligned.append({"text": line, "start": None, "end": None, "confidence": 0})
            else:
                aligned.append({"text": line, "start": None, "end": None, "confidence": 0})
        # Estimate timestamps for unmatched lines between confirmed ASR anchors.
        # Confirmed AI timestamps are never overwritten.
        anchors = [i for i, item in enumerate(aligned)
                   if item.get("start") is not None and item.get("end") is not None]
        if language == "or" and not anchors:
            raise ValueError(
                "Odia audio was transcribed, but none of the supplied Odia lyric lines matched the AI transcript. "
                "No fake estimated timings were saved. Check that the selected song is the same as these lyrics."
            )
        def weight(i):
            return max(1, len(tokens(aligned[i]["text"])))
        if anchors:
            first = anchors[0]
            if first > 0:
                weights = [weight(i) for i in range(first)]
                total = sum(weights)
                end_bound = max(0.0, float(aligned[first]["start"]))
                cursor_time = 0.0
                for i, w in enumerate(weights):
                    start_time = cursor_time
                    cursor_time += end_bound * w / total
                    aligned[i].update(start=round(start_time, 3),
                                      end=round(cursor_time, 3),
                                      confidence="estimated")
            for left, right in zip(anchors, anchors[1:]):
                if right - left <= 1:
                    continue
                begin = float(aligned[left]["end"])
                finish = float(aligned[right]["start"])
                if finish <= begin:
                    continue
                weights = [weight(i) for i in range(left + 1, right)]
                total = sum(weights)
                cursor_time = begin
                for i, w in zip(range(left + 1, right), weights):
                    start_time = cursor_time
                    cursor_time += (finish - begin) * w / total
                    aligned[i].update(start=round(start_time, 3),
                                      end=round(cursor_time, 3),
                                      confidence="estimated")
            last = anchors[-1]
            if last < len(aligned) - 1 and duration > float(aligned[last]["end"]):
                weights = [weight(i) for i in range(last + 1, len(aligned))]
                total = sum(weights)
                begin, finish = float(aligned[last]["end"]), float(duration)
                cursor_time = begin
                for i, w in zip(range(last + 1, len(aligned)), weights):
                    start_time = cursor_time
                    cursor_time += (finish - begin) * w / total
                    aligned[i].update(start=round(start_time, 3),
                                      end=round(cursor_time, 3),
                                      confidence="estimated")

        else:
            # If ASR could not match any lyric line, still create a full-song
            # estimated timeline so no lyric line is left without a time.
            if duration > 0 and aligned:
                weights = [weight(i) for i in range(len(aligned))]
                total = sum(weights)
                cursor_time = 0.0
                for i, w in enumerate(weights):
                    start_time = cursor_time
                    cursor_time += float(duration) * w / total
                    aligned[i].update(start=round(start_time, 3),
                                      end=round(cursor_time, 3),
                                      confidence="estimated")

        with _jobs_lock:
            _jobs[job_id] = {"status": "completed", "updated_at": time.time(), "result": {
                "language": detected_language, "selected_language": language, "duration": duration,
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
    try:
        lyric_line_count = validate_lyrics(lyrics, MAX_LYRICS_CHARS, MAX_LYRIC_LINES)
    except ValueError as exc:
        reason = str(exc)
        messages = {
            "empty_lyrics": "ପ୍ରଥମେ ସମ୍ପୂର୍ଣ୍ଣ ଗୀତିକା ଲେଖନ୍ତୁ।",
            "lyrics_too_long": "ଗୀତିକା ବହୁତ ଲମ୍ବା। ୩୦,୦୦୦ ଅକ୍ଷର ମଧ୍ୟରେ ରଖନ୍ତୁ।",
            "too_many_lyric_lines": "ଗୀତିକାରେ ସର୍ବାଧିକ ୫୦୦ଟି ଖାଲି ନଥିବା ଧାଡ଼ି ରଖନ୍ତୁ।",
            "no_lyric_lines": "ପଢ଼ିହେବା ଭଳି ଗୀତିକା ଧାଡ଼ି ମିଳିଲା ନାହିଁ। ପ୍ରତ୍ୟେକ ଧାଡ଼ିକୁ ଅଲଗା ଲାଇନ୍‌ରେ ଲେଖନ୍ତୁ।",
        }
        status_code = 413 if reason in {"lyrics_too_long", "too_many_lyric_lines"} else 400
        raise HTTPException(status_code, messages.get(reason, "ଗୀତିକା ଯାଞ୍ଚ ହୋଇପାରିଲା ନାହିଁ।")) from exc
    if language not in {"auto", "or", "hi", "en"}:
        raise HTTPException(400, "ସ୍ୱୟଂଚାଳିତ ଚିହ୍ନଟ, ଓଡ଼ିଆ, ହିନ୍ଦୀ କିମ୍ବା ଇଂରାଜୀ ବାଛନ୍ତୁ।")
    suffix = os.path.splitext(audio.filename or "audio.mp3")[1].lower() or ".mp3"
    if suffix not in ALLOWED_AUDIO:
        raise HTTPException(415, "ଏହି ଅଡିଓ ଫର୍ମାଟ୍ ସମର୍ଥିତ ନୁହେଁ। MP3, WAV, M4A, AAC, OGG, FLAC କିମ୍ବା WEBM ବ୍ୟବହାର କରନ୍ତୁ।")
    active_provider = select_transcription_provider(
        language,
        os.getenv("TRANSCRIPTION_PROVIDER", "auto"),
        bool(os.getenv("SARVAM_API_KEY", "").strip()),
        bool(os.getenv("GROQ_API_KEY", "").strip()),
    )
    upload_limit = 25 * 1024 * 1024 if active_provider == "groq" else MAX_AUDIO_BYTES

    def check_audio_size(size):
        try:
            return validate_audio_size(size, upload_limit)
        except ValueError as exc:
            if str(exc) == "audio_too_large":
                raise HTTPException(
                    413,
                    "ଅଡିଓ ଫାଇଲ୍ ଏହି provider ପାଇଁ ନିର୍ଦ୍ଧାରିତ ସୀମାଠାରୁ ବଡ଼। Groq: ୨୫ MB; Sarvam/local: ୪୦ MB।",
                ) from exc
            raise HTTPException(400, "ଖାଲି କିମ୍ବା ଅବୈଧ ଅଡିଓ ଫାଇଲ୍ ଅପଲୋଡ୍ ହୋଇଛି। ଦୟାକରି ସଠିକ୍ ଅଡିଓ ବାଛନ୍ତୁ।") from exc

    # Fast preflight avoids creating another processing temp file while busy.
    # Capacity is checked again under the lock after upload to close the race
    # between simultaneous requests.
    with _jobs_lock:
        if active_job_count(_jobs) >= MAX_ACTIVE_JOBS:
            raise HTTPException(429, BUSY_JOB_MESSAGE)

    path = None
    upload_started = time.time()
    logger.info("SYNC_UPLOAD_RECEIVED filename=%s language=%s content_length=%s",
                os.path.basename(audio.filename or "audio"), language,
                audio.headers.get("content-length", "unknown"))
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            path = tmp.name
            total = 0
            while True:
                chunk = await audio.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                check_audio_size(total)
                tmp.write(chunk)
        # Reject empty uploads before allocating a job or starting an AI request.
        check_audio_size(total)
        job_id = uuid.uuid4().hex
        with _jobs_lock:
            now = time.time()
            for old_id, old_job in list(_jobs.items()):
                if old_job.get("status") in {"completed", "failed"} and now - old_job.get("updated_at", now) > JOB_RETENTION_SECONDS:
                    _jobs.pop(old_id, None)
            if active_job_count(_jobs) >= MAX_ACTIVE_JOBS:
                raise HTTPException(429, BUSY_JOB_MESSAGE)
            _jobs[job_id] = {"status": "queued", "message": "ଅପଲୋଡ୍ ସଫଳ। AI ପ୍ରକ୍ରିୟା ପାଇଁ ଅପେକ୍ଷା କରନ୍ତୁ।", "updated_at": now}
            if len(_jobs) > 50:
                for old_id, old_job in list(_jobs.items()):
                    if old_job.get("status") in {"completed", "failed"}:
                        _jobs.pop(old_id, None)
                        if len(_jobs) <= 40:
                            break
        background_tasks.add_task(process_job, job_id, path, lyrics, language)
        path = None
        logger.info("SYNC_UPLOAD_RESPONSE job_id=%s status=queued audio_bytes=%s lyric_lines=%s elapsed_seconds=%.2f",
                    job_id, total, lyric_line_count, time.time() - upload_started)
        return {"job_id": job_id, "status": "queued"}
    finally:
        await audio.close()
        if path and os.path.exists(path):
            os.unlink(path)
