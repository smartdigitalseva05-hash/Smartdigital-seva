"""ASGI request-body limits applied before multipart upload parsing.

The sync endpoint accepts a bounded audio file plus bounded UTF-8 lyrics.
Checking Content-Length is a fast preflight; counting received chunks also
protects requests that omit the header or use chunked transfer encoding.
"""

from typing import Iterable


class RequestBodyLimitMiddleware:
    """Reject oversized request bodies on selected HTTP paths."""

    def __init__(self, app, max_body_bytes: int, paths: Iterable[str] = ("/api/sync",)):
        limit = int(max_body_bytes)
        if limit <= 0:
            raise ValueError("max_body_bytes must be a positive integer")
        self.app = app
        self.max_body_bytes = limit
        self.paths = frozenset(str(path) for path in paths)

    async def __call__(self, scope, receive, send):
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") not in self.paths
        ):
            await self.app(scope, receive, send)
            return

        length_values = [
            value for key, value in scope.get("headers", ())
            if key.lower() == b"content-length"
        ]
        if len(length_values) > 1:
            await self._reject(send, 400, "Invalid Content-Length header.")
            return
        if length_values:
            try:
                raw_length = length_values[0].decode("ascii")
                if not raw_length or not raw_length.isdigit():
                    raise ValueError("invalid decimal length")
                declared = int(raw_length)
            except (UnicodeDecodeError, ValueError):
                await self._reject(send, 400, "Invalid Content-Length header.")
                return
            if declared > self.max_body_bytes:
                await self._reject(send, 413, "Request body exceeds the maximum allowed size.")
                return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise _RequestBodyTooLarge
            return message

        response_started = False

        async def tracked_send(message):
            nonlocal response_started
            if message.get("type") == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracked_send)
        except _RequestBodyTooLarge:
            if response_started:
                raise
            await self._reject(send, 413, "Request body exceeds the maximum allowed size.")

    @staticmethod
    async def _reject(send, status_code: int, detail: str):
        body = ('{"detail":"' + detail + '"}').encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"cache-control", b"no-store"),
            ],
        })
        await send({"type": "http.response.body", "body": body})


class _RequestBodyTooLarge(Exception):
    """Internal signal used to stop reading an oversized request."""
