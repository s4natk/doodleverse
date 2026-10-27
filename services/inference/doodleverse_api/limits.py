"""Refuse request bodies over a byte limit before anything parses them."""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from doodleverse_api.errors import error_response


class BodySizeLimit:
    """413 when the declared or the streamed body passes `max_bytes`. The body is buffered up to the limit."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def _refuse(self, scope: Scope, receive: Receive, send: Send) -> None:
        response = error_response(413, "payload_too_large", f"The body is over {self.max_bytes:,} bytes.")
        await response(scope, receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.max_bytes:
            await self._refuse(scope, receive, send)
            return
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                await self._refuse(scope, receive, send)
                return
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        buffered: Message | None = {"type": "http.request", "body": b"".join(chunks), "more_body": False}

        async def replay() -> Message:
            nonlocal buffered
            if buffered is not None:
                message, buffered = buffered, None
                return message
            return await receive()

        await self.app(scope, replay, send)
