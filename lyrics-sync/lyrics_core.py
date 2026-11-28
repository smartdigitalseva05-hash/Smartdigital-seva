"""Unicode-safe lyric tokenization and timestamp helpers.

This module intentionally has no third-party dependencies so its behaviour can
be tested independently of the speech-to-text runtime.
"""
import math
import unicodedata
from urllib.parse import urlsplit


DEFAULT_CORS_ORIGINS = ("https://smartdigitalseva05-hash.github.io",)


def parse_allowed_origins(value=None):
    """Parse a comma-separated HTTP(S) origin allowlist without wildcards.

    An unset value uses the production GitHub Pages origin. An explicitly
    configured but invalid value fails closed by returning an empty list.
    """
    if value is None or not str(value).strip():
        return list(DEFAULT_CORS_ORIGINS)

    origins = []
    for candidate in str(value).split(","):
        candidate = candidate.strip()
        if not candidate or candidate == "*":
            continue
        try:
            parsed = urlsplit(candidate)
            parsed.port  # Validate an explicitly supplied port.
        except ValueError:
            continue
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            continue
        origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        if origin not in origins:
            origins.append(origin)
    return origins


def active_job_count(jobs):
    """Count queued/processing jobs in an in-memory job registry."""
    return sum(
        1 for job in jobs.values()
        if isinstance(job, dict) and job.get("status") in {"queued", "processing"}
    )


def validate_lyrics(text, max_chars=30000, max_lines=500):
    """Validate pasted lyrics and return the number of non-empty lines.

    Raises ValueError with a stable reason code so API layers can choose a
    localized message and HTTP status without duplicating the rules.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty_lyrics")
    if len(text) > max_chars:
        raise ValueError("lyrics_too_long")
    line_count = sum(1 for line in text.splitlines() if line.strip())
    if line_count == 0:
        raise ValueError("no_lyric_lines")
    if line_count > max_lines:
        raise ValueError("too_many_lyric_lines")
    return line_count


def validate_audio_size(size, max_bytes):
    """Validate a streamed upload size; zero-byte files are never valid audio."""
    try:
        size = int(size)
        max_bytes = int(max_bytes)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("invalid_audio_size") from None
    if max_bytes <= 0:
        raise ValueError("invalid_audio_limit")
    if size <= 0:
        raise ValueError("empty_audio")
    if size > max_bytes:
        raise ValueError("audio_too_large")
    return size


def select_transcription_provider(language, configured_provider, sarvam_key_present, groq_key_present):
    """Resolve provider once so diagnostics, upload limits and processing agree.

    Odia is intentionally pinned to Sarvam. For other languages, auto mode
    prefers Groq, then Sarvam, then local Whisper. A configured hosted provider
    falls back only when its own key is absent.
    """
    if language == "or":
        return "sarvam"
    setting = str(configured_provider or "auto").strip().lower()
    if setting not in {"", "auto", "groq", "sarvam", "local"}:
        setting = "auto"
    if setting in {"", "auto"}:
        if groq_key_present:
            return "groq"
        if sarvam_key_present:
            return "sarvam"
        return "local"
    if setting == "groq" and not groq_key_present:
        return "sarvam" if sarvam_key_present else "local"
    if setting == "sarvam" and not sarvam_key_present:
        return "groq" if groq_key_present else "local"
    return setting


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



def interpolate_unmatched_lines(aligned, duration):
    """Estimate only gaps adjacent to confirmed AI matches.

    When no lyric line matches the transcript, leave every line untimed. A
    fabricated full-song schedule looks authoritative but is not evidence of
    synchronization; users can choose the explicit No-AI timeline instead.
    The input list is updated in place and returned for convenient chaining.
    """
    if not isinstance(aligned, list) or not aligned:
        return aligned

    try:
        duration = float(duration)
    except (TypeError, ValueError, OverflowError):
        duration = 0.0
    if not math.isfinite(duration) or duration < 0:
        duration = 0.0

    anchors = []
    for index, item in enumerate(aligned):
        if not isinstance(item, dict):
            continue
        try:
            start = float(item.get("start"))
            end = float(item.get("end"))
        except (TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(start) and math.isfinite(end) and 0 <= start < end:
            anchors.append(index)

    # Do not invent a timeline when the ASR transcript matched no lyric line.
    if not anchors:
        return aligned

    def weight(index):
        return max(1, len(tokens(aligned[index].get("text", ""))))

    def fill(indices, begin, finish):
        indices = list(indices)
        if not indices or not math.isfinite(begin) or not math.isfinite(finish) or finish <= begin:
            return
        weights = [weight(index) for index in indices]
        total = sum(weights)
        cursor = begin
        for index, item_weight in zip(indices, weights):
            start = cursor
            cursor += (finish - begin) * item_weight / total
            if cursor > start:
                aligned[index].update(
                    start=round(start, 3),
                    end=round(cursor, 3),
                    confidence="estimated",
                )

    first = anchors[0]
    fill(range(0, first), 0.0, max(0.0, float(aligned[first]["start"])))

    for left, right in zip(anchors, anchors[1:]):
        fill(
            range(left + 1, right),
            float(aligned[left]["end"]),
            float(aligned[right]["start"]),
        )

    last = anchors[-1]
    last_end = float(aligned[last]["end"])
    if last < len(aligned) - 1 and duration > last_end:
        fill(range(last + 1, len(aligned)), last_end, duration)

    return aligned

def timed_tokens(text, start, end):
    """Split a phrase interval evenly across its Unicode word tokens.

    Invalid, non-finite, negative, or zero-length intervals are discarded so
    provider responses cannot introduce unusable timestamps into the editor.
    """
    parts = tokens(text)
    if not parts:
        return []
    try:
        start, end = float(start), float(end)
    except (TypeError, ValueError, OverflowError):
        return []
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
        return []
    span = end - start
    count = len(parts)
    return [
        {
            "token": part,
            "start": start + span * index / count,
            "end": start + span * (index + 1) / count,
        }
        for index, part in enumerate(parts)
    ]
