"""Unit tests for the dependency-free lyrics timing helpers."""
import math
import sys
import unicodedata
import unittest
from pathlib import Path

# unittest discovery adds the tests folder, not its parent, to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lyrics_core import timed_tokens, tokens, validate_lyrics, validate_audio_size, select_transcription_provider


class TokenizationTests(unittest.TestCase):
    def test_odia_words_keep_combining_marks(self):
        self.assertEqual(
            tokens("ଅଲେଖ, ମହିମା! ଜୟ ମହିମା।"),
            ["ଅଲେଖ", "ମହିମା", "ଜୟ", "ମହିମା"],
        )

    def test_nfc_and_decomposed_text_match(self):
        phrase = "ଓଡ଼ିଆ ଭାଷା"
        decomposed = unicodedata.normalize("NFD", phrase)
        self.assertEqual(tokens(phrase), tokens(decomposed))

    def test_latin_casefold_and_punctuation(self):
        self.assertEqual(tokens("JAYA Alekh—MAHIMA!"), ["jaya", "alekh", "mahima"])

    def test_empty_input_has_no_tokens(self):
        self.assertEqual(tokens(None), [])
        self.assertEqual(tokens("   । 🙏 "), [])


class TimingTests(unittest.TestCase):
    def test_phrase_interval_is_split_evenly(self):
        result = timed_tokens("ଜୟ ମହିମା", 2, 4)
        self.assertEqual([item["token"] for item in result], ["ଜୟ", "ମହିମା"])
        self.assertEqual(result[0]["start"], 2)
        self.assertEqual(result[0]["end"], 3)
        self.assertEqual(result[1]["start"], 3)
        self.assertEqual(result[1]["end"], 4)

    def test_single_word_keeps_full_interval(self):
        self.assertEqual(
            timed_tokens("Alekh", "1.25", "2.5"),
            [{"token": "alekh", "start": 1.25, "end": 2.5}],
        )

    def test_invalid_intervals_are_rejected(self):
        for start, end in ((-1, 2), (2, 2), (3, 2), ("bad", 4), (0, math.inf), (0, math.nan)):
            with self.subTest(start=start, end=end):
                self.assertEqual(timed_tokens("ଜୟ ମହିମା", start, end), [])

    def test_empty_phrase_has_no_timing(self):
        self.assertEqual(timed_tokens("🙏 !!!", 0, 2), [])


class InputValidationTests(unittest.TestCase):
    def test_lyrics_count_ignores_blank_lines_and_accepts_exact_limits(self):
        phrase = "ଜୟ\n\nମହିମା"
        self.assertEqual(validate_lyrics(phrase, max_chars=len(phrase), max_lines=2), 2)

    def test_empty_lyrics_are_rejected(self):
        for value in ("", "  \n  ", None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "empty_lyrics"):
                    validate_lyrics(value)

    def test_lyrics_character_limit_is_enforced(self):
        self.assertEqual(validate_lyrics("abc", max_chars=3, max_lines=1), 1)
        with self.assertRaisesRegex(ValueError, "lyrics_too_long"):
            validate_lyrics("abcd", max_chars=3, max_lines=1)

    def test_lyrics_nonempty_line_limit_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "too_many_lyric_lines"):
            validate_lyrics("one\n\ntwo\nthree", max_chars=100, max_lines=2)

    def test_audio_size_accepts_exact_limit(self):
        self.assertEqual(validate_audio_size(100, 100), 100)

    def test_empty_audio_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty_audio"):
            validate_audio_size(0, 100)

    def test_oversized_audio_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "audio_too_large"):
            validate_audio_size(101, 100)

    def test_invalid_audio_size_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid_audio_size"):
            validate_audio_size("not-a-size", 100)

    def test_odia_is_always_routed_to_sarvam(self):
        self.assertEqual(select_transcription_provider("or", "groq", True, True), "sarvam")
        self.assertEqual(select_transcription_provider("or", "auto", False, True), "sarvam")

    def test_auto_provider_priority_is_groq_then_sarvam_then_local(self):
        self.assertEqual(select_transcription_provider("hi", "auto", True, True), "groq")
        self.assertEqual(select_transcription_provider("en", "auto", True, False), "sarvam")
        self.assertEqual(select_transcription_provider("auto", "auto", False, False), "local")

    def test_explicit_provider_falls_back_only_when_its_key_is_missing(self):
        self.assertEqual(select_transcription_provider("hi", "groq", False, False), "local")
        self.assertEqual(select_transcription_provider("hi", "groq", True, False), "sarvam")
        self.assertEqual(select_transcription_provider("en", "sarvam", False, True), "groq")
        self.assertEqual(select_transcription_provider("en", "groq", False, True), "groq")


if __name__ == "__main__":
    unittest.main()
