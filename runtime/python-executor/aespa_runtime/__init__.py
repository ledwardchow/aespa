"""Tiny synchronous SDK exposed to AESPA's network-disabled Python sandbox."""

from __future__ import annotations

import base64
import json
import os
import socket
import threading
import uuid
from dataclasses import dataclass
from typing import Any


class PolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Response:
    status_code: int
    headers: dict[str, str]
    body: bytes
    url: str
    duration_ms: int | None
    traffic_id: int | None
    redirect_blocked: str | None = None
    stored_session: str | None = None

    @property
    def text(self) -> str:
        return self.body.decode(errors="replace")

    def json(self) -> Any:
        return json.loads(self.body)


_fd = int(os.environ["AESPA_BROKER_FD"])
_sock = socket.socket(fileno=_fd)
_stream = _sock.makefile("rwb", buffering=0)
_lock = threading.Lock()


def _encode_request(spec: dict[str, Any]) -> dict[str, Any]:
    data = dict(spec)
    body = data.pop("body", None)
    json_body = data.pop("json", None)
    form = data.pop("form", None)
    selected = sum(value is not None for value in (body, json_body, form))
    if selected > 1:
        raise ValueError("provide only one of body, json, or form")
    if isinstance(body, str):
        data["body_text"] = body
    elif body is not None:
        data["body_b64"] = base64.b64encode(bytes(body)).decode()
    elif json_body is not None:
        data["json"] = json_body
    elif form is not None:
        data["form"] = form
    return data


def _rpc(op: str, payload: dict[str, Any]) -> dict[str, Any]:
    request_id = uuid.uuid4().hex
    message = {"type": op, "request_id": request_id, **payload}
    encoded = (json.dumps(message, separators=(",", ":")) + "\n").encode()
    with _lock:
        _stream.write(encoded)
        raw = _stream.readline()
    if not raw:
        raise RuntimeError("AESPA broker disconnected")
    reply = json.loads(raw)
    if reply.get("request_id") != request_id:
        raise RuntimeError("AESPA broker returned a mismatched response")
    if not reply.get("ok"):
        if reply.get("error_type") == "policy":
            raise PolicyError(str(reply.get("error") or "request denied"))
        raise RuntimeError(str(reply.get("error") or "broker request failed"))
    return reply


def _response(reply: dict[str, Any]) -> Response:
    return Response(
        status_code=int(reply.get("status_code") or 0),
        headers=dict(reply.get("headers") or {}),
        body=base64.b64decode(reply.get("body_b64") or ""),
        url=str(reply.get("url") or ""),
        duration_ms=reply.get("duration_ms"),
        traffic_id=reply.get("traffic_id"),
        redirect_blocked=reply.get("redirect_blocked"),
        stored_session=reply.get("stored_session"),
    )


def request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | str | None = None,
    json: Any = None,
    form: dict[str, Any] | None = None,
    use_session: str | None = None,
    store_as: str | None = None,
    page_id: int | None = None,
    owasp_category: str | None = None,
    test_class: str | None = None,
    obligation_id: int | None = None,
    note: str | None = None,
) -> Response:
    spec = _encode_request(locals())
    return _response(_rpc("broker.request", {"request": spec}))


def request_batch(
    requests: list[dict[str, Any]], *, concurrency: int = 2
) -> list[Response]:
    encoded = [_encode_request(item) for item in requests]
    reply = _rpc(
        "broker.request_batch", {"requests": encoded, "concurrency": concurrency}
    )
    return [_response(item) for item in reply.get("responses") or []]
