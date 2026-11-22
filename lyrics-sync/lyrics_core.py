"""Unicode-safe lyric tokenization and timestamp helpers.

This module intentionally has no third-party dependencies so its behaviour can
be tested independently of the speech-to-text runtime.
"""
import math
import unicodedata


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
