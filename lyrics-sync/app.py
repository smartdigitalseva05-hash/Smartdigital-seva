from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel
from difflib import SequenceMatcher
import tempfile, os, re

app = FastAPI(title="Auto Lyrics Sync API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_model = None

def get_model():
    global _model
    if _model is None:
        _model = WhisperModel(os.getenv("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    return _model

def tokens(text):
    # Keep Unicode letters (including Odia/Hindi) and digits.
    return re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)

@app.get("/")
def health():
    return {"status":"ok","service":"Auto Lyrics Sync API"}

@app.post("/api/sync")
async def sync(audio: UploadFile = File(...), lyrics: str = Form(...), language: str = Form("auto")):
    if not lyrics.strip():
        raise HTTPException(400, "Paste the full lyrics first.")
    suffix = os.path.splitext(audio.filename or "audio.mp3")[1] or ".mp3"
    data = await audio.read()
    if len(data) > 40 * 1024 * 1024:
        raise HTTPException(413, "Audio file must be 40 MB or smaller.")
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data); path = tmp.name
        model = get_model()
        lang = None if language == "auto" else language
        segments, info = model.transcribe(path, language=lang, word_timestamps=True, vad_filter=True, beam_size=5)
        words, transcript = [], []
        for seg in segments:
            transcript.append(seg.text)
            if seg.words:
                for w in seg.words:
                    ts = tokens(w.word)
                    if ts: words.append({"token":ts[0], "start":float(w.start), "end":float(w.end)})
        if not words:
            raise HTTPException(422, "Speech could not be detected. Try clearer audio or another language setting.")
        lyric_lines = [x.strip() for x in lyrics.splitlines() if x.strip()]
        aligned, cursor = [], 0
        for line in lyric_lines:
            target = tokens(line)
            if not target:
                continue
            best, score_best = None, 0.0
            # Greedy forward search; singing/transcription errors can reduce matching accuracy.
            for start in range(cursor, min(len(words), cursor + 120)):
                lo, hi = max(1, len(target)-4), min(len(target)+6, len(words)-start)
                for length in range(lo, hi+1):
                    heard = [w["token"] for w in words[start:start+length]]
                    score = SequenceMatcher(None, target, heard).ratio()
                    if score > score_best:
                        best, score_best = (start, start+length-1), score
            if best and score_best >= 0.30:
                a,b = best
                aligned.append({"text":line,"start":words[a]["start"],"end":words[b]["end"],"confidence":round(score_best,2)})
                cursor = max(cursor,b+1)
            else:
                aligned.append({"text":line,"start":None,"end":None,"confidence":0})
        return {"language":info.language,"duration":info.duration,"lines":aligned,"transcript":" ".join(transcript)}
    finally:
        if path and os.path.exists(path): os.unlink(path)
