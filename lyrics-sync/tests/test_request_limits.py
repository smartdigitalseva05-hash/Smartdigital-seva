"""Tests for the ASGI request-body guard used by the sync upload endpoint."""

import sys
import unittest
from pathlib import Path

# unittest discovery starts in the tests directory; expose the project modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from request_limits import RequestBodyLimitMiddleware


class RequestBodyLimitTests(unittest.IsolatedAsyncioTestCase):
    async def _invoke(self, messages, headers=(), path="/api/sync", method="POST"):
        remaining = list(messages)
        sent = []
        app_called = False

        async def receive():
            if remaining:
                return remaining.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        async def app(scope, inner_receive, inner_send):
            nonlocal app_called
            app_called = True
            body = bytearray()
            while True:
                message = await inner_receive()
                if message["type"] == "http.disconnect":
                    return
                body.extend(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            await inner_send({"type": "http.response.start", "status": 200, "headers": []})
            await inner_send({"type": "http.response.body", "body": bytes(body)})

        middleware = RequestBodyLimitMiddleware(app, max_body_bytes=5)
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": list(headers),
        }
        await middleware(scope, receive, send)
        return sent, app_called

    @staticmethod
    def _status(messages):
        return next(message["status"] for message in messages
                    if message["type"] == "http.response.start")

    async def test_exact_limit_is_allowed(self):
        messages, app_called = await self._invoke(
            [{"type": "http.request", "body": b"12345", "more_body": False}],
            headers=((b"content-length", b"5"),),
        )
        self.assertTrue(app_called)
        self.assertEqual(self._status(messages), 200)
        self.assertEqual(messages[-1]["body"], b"12345")

    async def test_oversized_content_length_is_rejected_before_app(self):
        messages, app_called = await self._invoke(
            [],
            headers=((b"content-length", b"6"),),
        )
        self.assertFalse(app_called)
        self.assertEqual(self._status(messages), 413)

    async def test_chunked_body_is_counted_without_content_length(self):
        messages, app_called = await self._invoke([
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"456", "more_body": False},
        ])
        self.assertTrue(app_called)
        self.assertEqual(self._status(messages), 413)

    async def test_understated_content_length_does_not_bypass_limit(self):
        messages, app_called = await self._invoke(
            [{"type": "http.request", "body": b"123456", "more_body": False}],
            headers=((b"content-length", b"1"),),
        )
        self.assertTrue(app_called)
        self.assertEqual(self._status(messages), 413)

    async def test_malformed_or_duplicate_content_length_is_rejected(self):
        for headers in (
            ((b"content-length", b"five"),),
            ((b"content-length", b"-1"),),
            ((b"content-length", b"2"), (b"content-length", b"2")),
        ):
            with self.subTest(headers=headers):
                messages, app_called = await self._invoke([], headers=headers)
                self.assertFalse(app_called)
                self.assertEqual(self._status(messages), 400)

    async def test_other_routes_are_not_limited(self):
        messages, app_called = await self._invoke(
            [{"type": "http.request", "body": b"123456", "more_body": False}],
            headers=((b"content-length", b"6"),),
            path="/",
            method="POST",
        )
        self.assertTrue(app_called)
        self.assertEqual(self._status(messages), 200)


if __name__ == "__main__":
    unittest.main()
