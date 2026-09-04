"""Trusted container-side harness separating user output from broker frames."""

from __future__ import annotations

import base64
import json
import os
import selectors
import socket
import subprocess
import sys
from pathlib import Path


def emit(value: dict) -> None:
    sys.stdout.write(json.dumps(value, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    raw = sys.stdin.readline()
    if not raw:
        return 2
    start = json.loads(raw)
    if start.get("type") != "execution.start" or start.get("protocol_version") != "1":
        emit({"type": "execution.error", "error": "unsupported start frame"})
        return 2
    code = str(start.get("code") or "")
    work_dir = Path(os.environ.get("AESPA_WORK_DIR", "/work"))
    script_path = work_dir / "script.py"
    with script_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(code)

    parent_sock, child_sock = socket.socketpair()
    env = {
        "LANG": "C.UTF-8",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONHASHSEED": "0",
        "AESPA_BROKER_FD": str(child_sock.fileno()),
    }
    proc = subprocess.Popen(
        [
            sys.executable,
            "-I",
            str(Path(__file__).with_name("aespa_child.py")),
            str(script_path),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=(child_sock.fileno(),),
        env=env,
        cwd=work_dir,
    )
    child_sock.close()
    parent_sock.setblocking(False)
    selector = selectors.DefaultSelector()
    selector.register(parent_sock, selectors.EVENT_READ, "rpc")
    selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
    selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
    rpc_buffer = b""
    while proc.poll() is None or selector.get_map():
        for key, _ in selector.select(timeout=0.1):
            chunk = (
                key.fileobj.recv(65536)
                if key.data == "rpc"
                else os.read(key.fileobj.fileno(), 65536)
            )
            if not chunk:
                selector.unregister(key.fileobj)
                continue
            if key.data in {"stdout", "stderr"}:
                emit(
                    {
                        "type": f"{key.data}.chunk",
                        "data_b64": base64.b64encode(chunk).decode(),
                    }
                )
                continue
            rpc_buffer += chunk
            while b"\n" in rpc_buffer:
                line, rpc_buffer = rpc_buffer.split(b"\n", 1)
                try:
                    message = json.loads(line)
                except Exception:
                    parent_sock.sendall(
                        b'{"ok":false,"error":"invalid broker frame"}\n'
                    )
                    continue
                if message.get("type") not in {
                    "broker.request",
                    "broker.request_batch",
                }:
                    parent_sock.sendall(
                        b'{"ok":false,"error_type":"policy",'
                        b'"error":"unsupported broker operation"}\n'
                    )
                    continue
                emit(message)
                reply_raw = sys.stdin.readline()
                if not reply_raw:
                    proc.terminate()
                    return 3
                parent_sock.sendall(reply_raw.encode())
    return_code = proc.wait()
    emit({"type": "execution.result", "exit_code": return_code})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
