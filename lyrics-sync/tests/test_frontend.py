"""Static contract checks for the browser-based Lyrics Sync page.

These tests deliberately use only the Python standard library so CI can
validate the frontend without installing browser automation dependencies.
"""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import unittest


class LyricsPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.label_targets = []
        self.script_count = 0
        self.script_text = []
        self._inside_script = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        if tag == "label" and attributes.get("for"):
            self.label_targets.append(attributes["for"])
        if tag == "script":
            self.script_count += 1
            self._inside_script = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "script":
            self._inside_script = False

    def handle_endtag(self, tag):
        if tag == "script":
            self._inside_script = False

    def handle_data(self, data):
        if self._inside_script:
            self.script_text.append(data)


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        page_path = Path(__file__).resolve().parents[1] / "index.html"
        cls.page = page_path.read_text(encoding="utf-8")
        cls.parser = LyricsPageParser()
        cls.parser.feed(cls.page)
        cls.parser.close()
        cls.ids = [
            attrs["id"]
            for _, attrs in cls.parser.elements
            if attrs.get("id")
        ]

    def test_element_ids_are_unique(self):
        duplicates = [
            element_id
            for element_id, count in Counter(self.ids).items()
            if count > 1
        ]
        self.assertEqual(duplicates, [], "Duplicate HTML IDs break DOM lookups.")

    def test_required_controls_exist(self):
        required = {
            "audio", "lyrics", "lang", "api", "testApi", "go", "noAiSync",
            "out", "preview", "srt", "json", "videoExport", "status", "list",
        }
        self.assertTrue(required.issubset(set(self.ids)),
                        "Missing controls: " + ", ".join(sorted(required - set(self.ids))))

    def test_label_targets_resolve(self):
        missing = sorted(set(self.parser.label_targets) - set(self.ids))
        self.assertEqual(missing, [], "Labels reference missing element IDs.")

    def test_audio_picker_accepts_audio_files(self):
        audio_inputs = [
            attrs for tag, attrs in self.parser.elements
            if tag == "input" and attrs.get("id") == "audio"
        ]
        self.assertEqual(len(audio_inputs), 1)
        self.assertIn("audio/*", audio_inputs[0].get("accept", ""))

    def test_sync_and_job_status_api_contract_is_present(self):
        self.assertIn("/api/sync", self.page)
        self.assertIn("/api/jobs/", self.page)

    def test_caption_and_video_exports_are_available(self):
        self.assertTrue({"srt", "json", "videoExport", "videoRatio"}.issubset(set(self.ids)))

    def test_backend_cors_uses_an_explicit_origin_allowlist(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        backend = app_path.read_text(encoding="utf-8")
        self.assertIn("parse_allowed_origins", backend)
        self.assertIn("allow_origins=allowed_origins", backend)
        self.assertNotIn('allow_origins=["*"]', backend)

    def test_upload_body_limit_runs_before_multipart_parser(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        backend = app_path.read_text(encoding="utf-8")
        self.assertIn("RequestBodyLimitMiddleware", backend)
        self.assertIn("MAX_REQUEST_BODY_BYTES", backend)
        self.assertIn('paths=("/api/sync",)', backend)
        guard_registration = backend.index("    RequestBodyLimitMiddleware,")
        trace_registration = backend.index('@app.middleware("http")')
        cors_registration = backend.index("    CORSMiddleware,")
        self.assertLess(guard_registration, trace_registration)
        self.assertLess(trace_registration, cors_registration,
                        "CORS must wrap the body guard so browsers can read 413 errors.")

    def test_ai_timing_uses_conservative_interpolation_helper(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        backend = app_path.read_text(encoding="utf-8")
        self.assertIn("interpolate_unmatched_lines", backend)
        self.assertNotIn("full-song\\n            # estimated timeline", backend)

    def test_inline_javascript_is_present(self):
        self.assertGreater(self.parser.script_count, 0)
        self.assertTrue("".join(self.parser.script_text).strip())


if __name__ == "__main__":
    unittest.main()
