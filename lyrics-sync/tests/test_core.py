"""Unit tests for the dependency-free lyrics timing helpers."""
import math
import sys
import unicodedata
import unittest
from pathlib import Path

# unittest discovery adds the tests folder, not its parent, to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lyrics_core import timed_tokens, tokens


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


if __name__ == "__main__":
    unittest.main()
