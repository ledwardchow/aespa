"""Stable ASGI dispatcher for extension-owned API routes."""

from __future__ import annotations

from urllib.parse import unquote

from aespa.extensions.runtime import get_extension_manager


class ExtensionApiDispatcher:
    """Dispatch ``/extension/<id>/...`` without mutating the core route table."""

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self._not_found(scope, receive, send)
            return
        relative = scope.get("path", "").lstrip("/")
        if relative.startswith("extension/"):
            relative = relative.removeprefix("extension/")
        extension_id, separator, remainder = relative.partition("/")
        extension_id = unquote(extension_id)
        manager = get_extension_manager()
        manager.ensure_loaded()
        record = manager.extensions.get(extension_id)
        app = manager.api_app_for(extension_id)
        if (
            not separator
            or record is None
            or not record.enabled
            or record.status != "loaded"
            or app is None
        ):
            await self._not_found(scope, receive, send)
            return
        child_scope = dict(scope)
        child_scope["root_path"] = (
            scope.get("root_path", "") + f"/extension/{extension_id}"
        )
        child_scope["path"] = f"/{remainder}"
        child_scope["raw_path"] = child_scope["path"].encode("utf-8")
        await app(child_scope, receive, send)

    @staticmethod
    async def _not_found(scope, receive, send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        body = b'{"detail":"Extension API not found"}'
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
