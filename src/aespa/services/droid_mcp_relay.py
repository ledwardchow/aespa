"""Minimal stdio MCP relay used only by the Factory Droid adapter."""

from __future__ import annotations

import json
import socket
import sys
from typing import Any


def _write(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _forward(host: str, port: int, token: str, params: dict[str, Any]) -> dict:
    with socket.create_connection((host, port), timeout=180) as connection:
        stream = connection.makefile("rwb")
        stream.write(
            (
                json.dumps({"token": token, "params": params}, separators=(",", ":"))
                + "\n"
            ).encode()
        )
        stream.flush()
        line = stream.readline()
    if not line:
        raise RuntimeError("AESPA closed the Droid tool bridge")
    return json.loads(line)


def main() -> None:
    host, port, token, tools_json = sys.argv[1:5]
    tools = json.loads(tools_json)
    for line in sys.stdin:
        request: Any = None
        try:
            request = json.loads(line)
            method = request.get("method")
            request_id = request.get("id")
            if method == "notifications/initialized":
                continue
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "aespa", "version": "1"},
                }
            elif method == "tools/list":
                result = {"tools": tools}
            elif method == "tools/call":
                result = _forward(host, int(port), token, request.get("params") or {})
            else:
                _write(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "Method not found"},
                    }
                )
                continue
            if request_id is not None:
                _write({"jsonrpc": "2.0", "id": request_id, "result": result})
        except Exception as exc:
            _write(
                {
                    "jsonrpc": "2.0",
                    "id": request.get("id") if isinstance(request, dict) else None,
                    "error": {"code": -32603, "message": str(exc)},
                }
            )


if __name__ == "__main__":
    main()
