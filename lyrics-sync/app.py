from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from difflib import SequenceMatcher
import tempfile, os, re

app = FastAPI(title="Auto Lyrics Sync API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://smartdigitalseva05-hash.github.io"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
_model = None
MAX_AUDIO_BYTES = 40 * 1024 * 1024
MAX_LYRICS_CHARS = 30000
ALLOWED_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".mp4"}

def get_model():
    global _model
    if _model is None:
        # tiny is a lighter default for limited-memory hosting; set WHISPER_MODEL=small
        # on a server with enough RAM for potentially better recognition.
        _model = WhisperModel(
            os.getenv("WHISPER_MODEL", "tiny"),
            device="cpu",
            compute_type="int8",
        )
    return _model

def tokens(text):
    # Keep Unicode letters (including Odia/Hindi) and digits.
    return re.findall(r"[^\\W_]+", text.lower(), flags=re.UNICODE)

@app.get("/")
def health():
    return {"status": "ok", "service": "Auto Lyrics Sync API"}

@app.post("/api/sync")
async def sync(
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

        model = get_model()
        lang = None if language == "auto" else language
        segments, info = model.transcribe(
            path,
            language=lang,
            word_timestamps=True,
            vad_filter=True,
            beam_size=3,
        )
        words, transcript = [], []
        for seg in segments:
            transcript.append(seg.text)
            if seg.words:
                for word in seg.words:
                    found = tokens(word.word)
                    if found:
                        words.append({
                            "token": found[0],
                            "start": float(word.start),
                            "end": float(word.end),
                        })

        if not words:
            raise HTTPException(
                422,
                "Speech could not be detected. Try clearer audio or another language setting.",
            )

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
                aligned.append({
                    "text": line,
                    "start": words[first]["start"],
                    "end": words[last]["end"],
                    "confidence": round(best_score, 2),
                })
                cursor = max(cursor, last + 1)
            else:
                aligned.append({
                    "text": line,
                    "start": None,
                    "end": None,
                    "confidence": 0,
                })

        return {
            "language": info.language,
            "duration": info.duration,
            "lines": aligned,
            "transcript": " ".join(transcript),
        }
    finally:
        await audio.close()
        if path and os.path.exists(path):
            os.unlink(path)
