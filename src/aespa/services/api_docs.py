"""Parse API documentation files into ``ApiEndpoint`` and ``ApiCredential`` rows.

Dispatch is by ``ApiDocument.doc_type``:
  3a  openapi / swagger  — walk OpenAPI 3.x / Swagger 2.x ``paths``
  3b  postman            — walk Postman Collection v2/v2.1 item tree
  3c  credentials        — parse bearer/key:value/curl -H/-b lines → ``ApiCredential``
  3d  freetext           — LLM extraction of endpoint list + auth notes
  3e  source_zip         — safe-unzip, framework-heuristic route scanning (+ optional LLM)
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

import yaml
from sqlmodel import Session, select

from aespa.models import ApiCollection, ApiCredential, ApiDocument, ApiEndpoint

if TYPE_CHECKING:
    pass

# ── Safety limits ─────────────────────────────────────────────────────────────

_MAX_ZIP_ENTRIES = 5_000
_MAX_ZIP_TOTAL_BYTES = 100 * 1024 * 1024   # 100 MiB uncompressed
_MAX_ZIP_SINGLE_BYTES = 10 * 1024 * 1024   # 10 MiB per entry
_MAX_FREETEXT_LLM_CHARS = 40_000


class ParseError(Exception):
    pass


# ── Public entry point ────────────────────────────────────────────────────────

async def parse_document(session: Session, collection_id: int, document_id: int) -> None:
    """Parse a stored document into endpoints/credentials; update its status.

    Idempotent: existing endpoints from the same doc are replaced.
    """
    doc = session.get(ApiDocument, document_id)
    if doc is None or doc.collection_id != collection_id:
        raise ParseError(f"Document {document_id} not found in collection {collection_id}")

    content = Path(doc.stored_path).read_bytes()

    # Re-sniff doc_type from content on every parse so that a misclassified
    # upload corrects itself on the first explicit reparse.
    from aespa.services.api_documents import _sniff_doc_type
    doc.doc_type = _sniff_doc_type(doc.filename, content)

    # Remove any existing endpoints from this doc so re-parse is clean.
    _delete_endpoints_for_doc(session, document_id)

    try:
        endpoints: list[dict] = []
        credentials: list[dict] = []

        if doc.doc_type in ("openapi", "swagger"):
            endpoints = _parse_openapi(content, doc)
            _update_collection_auth_summary(session, collection_id, content)
        elif doc.doc_type == "postman":
            endpoints, credentials = _parse_postman(content, doc)
        elif doc.doc_type == "credentials":
            credentials = _parse_credentials(content)
        elif doc.doc_type == "freetext":
            endpoints = await _parse_freetext(session, content, doc)
        elif doc.doc_type == "source_zip":
            endpoints = _parse_source_zip(content, doc)
        else:
            # unknown — attempt freetext LLM fallback
            endpoints = await _parse_freetext(session, content, doc)

        _upsert_endpoints(session, collection_id, document_id, endpoints)
        _upsert_credentials(session, collection_id, credentials)

        doc.status = "parsed"
        doc.error_message = None
    except Exception as exc:
        doc.status = "failed"
        doc.error_message = str(exc)[:1000]

    session.add(doc)
    session.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _delete_endpoints_for_doc(session: Session, document_id: int) -> None:
    existing = list(
        session.exec(
            select(ApiEndpoint).where(ApiEndpoint.source_doc_id == document_id)
        ).all()
    )
    for ep in existing:
        session.delete(ep)
    session.flush()


def _upsert_endpoints(
    session: Session,
    collection_id: int,
    document_id: int,
    endpoints: list[dict],
) -> None:
    """Insert endpoints, deduplicating by (method, normalized path) within the collection."""
    existing_keys: set[tuple[str, str]] = set()
    for ep in session.exec(
        select(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
    ).all():
        existing_keys.add((_norm_method(ep.method), _norm_path(ep.path)))

    for ep_data in endpoints:
        key = (_norm_method(ep_data.get("method", "GET")), _norm_path(ep_data.get("path", "/")))
        if key in existing_keys:
            continue
        existing_keys.add(key)
        ep = ApiEndpoint(
            collection_id=collection_id,
            source_doc_id=document_id,
            method=ep_data.get("method", "GET").upper(),
            path=ep_data.get("path", "/"),
            base_url=ep_data.get("base_url"),
            operation_id=ep_data.get("operation_id"),
            summary=ep_data.get("summary"),
            parameters_json=json.dumps(ep_data.get("parameters", [])),
            request_body_schema_json=json.dumps(ep_data.get("request_body", {})),
            response_schema_json=json.dumps(ep_data.get("response", {})),
            security_json=json.dumps(ep_data.get("security", [])),
            auth_required=bool(ep_data.get("auth_required", False)),
            tags_json=json.dumps(ep_data.get("tags", [])),
            sample_request_json=json.dumps(ep_data.get("sample_request", {})),
        )
        session.add(ep)
    session.flush()


def _upsert_credentials(
    session: Session, collection_id: int, credentials: list[dict]
) -> None:
    for cred_data in credentials:
        cred = ApiCredential(
            collection_id=collection_id,
            scheme=cred_data.get("scheme", "bearer"),
            name=cred_data.get("name", "Authorization"),
            value=cred_data.get("value", ""),
            label=cred_data.get("label"),
            scope=cred_data.get("scope", "global"),
        )
        session.add(cred)
    session.flush()


def _update_collection_auth_summary(
    session: Session, collection_id: int, content: bytes
) -> None:
    try:
        spec = _load_yaml_or_json(content)
        schemes = (
            spec.get("components", {}).get("securitySchemes", {})
            or spec.get("securityDefinitions", {})
        )
        if schemes:
            col = session.get(ApiCollection, collection_id)
            if col is not None:
                existing = json.loads(col.servers or "{}") if col.servers else {}
                existing["securitySchemes"] = schemes
                col.servers = json.dumps(existing)
                session.add(col)
    except Exception:
        pass


def _norm_method(m: str) -> str:
    return m.upper().strip()


def _norm_path(p: str) -> str:
    """Normalise path for dedup: lowercase, collapse double slashes, strip trailing slash."""
    p = p.strip().lower()
    p = re.sub(r"/+", "/", p)
    return p.rstrip("/") or "/"


# ── 3a OpenAPI / Swagger ──────────────────────────────────────────────────────

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def _load_yaml_or_json(content: bytes) -> dict:
    try:
        text = content.decode("utf-8", errors="replace")
        return yaml.safe_load(text) or {}
    except Exception:
        pass
    try:
        return json.loads(content) or {}
    except Exception:
        return {}


def _openapi_server_urls(spec: dict) -> list[str]:
    """Extract base URLs from OpenAPI 3.x servers or Swagger 2.x host/basePath."""
    urls = []
    for s in spec.get("servers", []):
        if isinstance(s, dict) and s.get("url"):
            urls.append(s["url"])
    if not urls:
        host = spec.get("host", "")
        base_path = spec.get("basePath", "/")
        scheme = next(iter(spec.get("schemes", ["https"])), "https")
        if host:
            urls.append(f"{scheme}://{host}{base_path}")
    return urls


def _resolve_schema_ref(spec: dict, obj: dict | None) -> dict:
    if obj is None:
        return {}
    ref = obj.get("$ref", "")
    if not ref.startswith("#/"):
        return obj
    parts = ref.lstrip("#/").split("/")
    node: dict = spec
    try:
        for p in parts:
            node = node[p]
        return node
    except (KeyError, TypeError):
        return obj


def _parse_openapi(content: bytes, doc: ApiDocument) -> list[dict]:
    spec = _load_yaml_or_json(content)
    if not isinstance(spec, dict):
        raise ParseError("Could not parse as YAML/JSON")

    server_urls = _openapi_server_urls(spec)
    base_url = server_urls[0] if server_urls else None

    # Swagger 2 global security, OpenAPI 3 global security
    global_security = spec.get("security", [])

    endpoints = []
    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        # Path-level parameters shared across methods
        path_params = path_item.get("parameters", [])

        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            security = operation.get("security", global_security)
            auth_required = bool(security)

            params = []
            for p in path_params + operation.get("parameters", []):
                resolved = _resolve_schema_ref(spec, p) if isinstance(p, dict) else p
                if isinstance(resolved, dict):
                    params.append({
                        "name": resolved.get("name", ""),
                        "in": resolved.get("in", ""),
                        "required": resolved.get("required", False),
                    })

            # Request body (OpenAPI 3)
            req_body: dict = {}
            rb = operation.get("requestBody", {})
            if rb:
                content_map = rb.get("content", {})
                for media_type, media_obj in content_map.items():
                    schema = _resolve_schema_ref(spec, media_obj.get("schema", {}))
                    req_body = {"media_type": media_type, "schema": schema}
                    break

            # Example request (OpenAPI 3 examples / Swagger 2 body param example)
            sample: dict = {}
            for p in operation.get("parameters", []):
                resolved = _resolve_schema_ref(spec, p) if isinstance(p, dict) else {}
                if resolved.get("in") == "body" and resolved.get("example"):
                    sample = resolved["example"]
                    break
            if not sample and rb:
                for media_obj in rb.get("content", {}).values():
                    if media_obj.get("example"):
                        sample = media_obj["example"]
                        break
                    for ex in (media_obj.get("examples") or {}).values():
                        if isinstance(ex, dict) and ex.get("value"):
                            sample = ex["value"]
                            break
                    if sample:
                        break

            endpoints.append({
                "method": method.upper(),
                "path": path,
                "base_url": base_url,
                "operation_id": operation.get("operationId"),
                "summary": operation.get("summary"),
                "parameters": params,
                "request_body": req_body,
                "security": security,
                "auth_required": auth_required,
                "tags": operation.get("tags", []),
                "sample_request": sample,
            })

    if not endpoints:
        raise ParseError("No paths/operations found in OpenAPI spec")
    return endpoints


# ── 3b Postman collection ─────────────────────────────────────────────────────

def _postman_method_url(item: dict) -> tuple[str, str, str | None]:
    req = item.get("request", {})
    if isinstance(req, str):
        return "GET", req, None
    method = (req.get("method") or "GET").upper()
    url = req.get("url", "")
    if isinstance(url, dict):
        raw = url.get("raw", "")
        host_parts = url.get("host", [])
        path_parts = url.get("path", [])
        base = ".".join(host_parts) if host_parts else ""
        path = "/" + "/".join(str(p) for p in path_parts) if path_parts else "/"
        # Replace postman variables {{var}} with {var}
        path = re.sub(r"\{\{(\w+)\}\}", r"{\1}", path)
        # Derive base_url from raw (protocol + host)
        m = re.match(r"(https?://[^/]+)", raw)
        base_url = m.group(1) if m else None
        return method, path, base_url
    url_str = str(url)
    url_str = re.sub(r"\{\{(\w+)\}\}", r"{\1}", url_str)
    parsed = urlparse(url_str)
    base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else None
    path = parsed.path or "/"
    return method, path, base_url


def _postman_auth(item: dict) -> tuple[bool, list[dict]]:
    auth = item.get("request", {}).get("auth") if isinstance(item.get("request"), dict) else None
    if not auth or not isinstance(auth, dict):
        return False, []
    auth_type = auth.get("type", "").lower()
    if auth_type == "noauth":
        return False, []
    scheme = "bearer" if auth_type in ("bearer",) else "apikey" if auth_type == "apikey" else "other"
    return True, [{"security_type": auth_type, "scheme": scheme}]


def _postman_body_example(item: dict) -> dict:
    req = item.get("request", {})
    if not isinstance(req, dict):
        return {}
    body = req.get("body", {})
    if not body:
        return {}
    mode = body.get("mode", "")
    if mode == "raw":
        raw = body.get("raw", "")
        try:
            return json.loads(raw)
        except Exception:
            return {}
    if mode == "urlencoded":
        return {p["key"]: p.get("value", "") for p in (body.get("urlencoded") or []) if "key" in p}
    if mode == "formdata":
        return {p["key"]: p.get("value", "") for p in (body.get("formdata") or []) if "key" in p}
    return {}


def _walk_postman_items(items: list, base_url: str | None = None) -> list[dict]:
    """Recursively walk Postman collection items / folders."""
    endpoints = []
    for item in items:
        if not isinstance(item, dict):
            continue
        # Folder
        if "item" in item:
            folder_endpoints = _walk_postman_items(item["item"], base_url)
            endpoints.extend(folder_endpoints)
            continue
        if "request" not in item:
            continue
        try:
            method, path, item_base_url = _postman_method_url(item)
            auth_required, security = _postman_auth(item)
            sample = _postman_body_example(item)
            endpoints.append({
                "method": method,
                "path": path,
                "base_url": item_base_url or base_url,
                "operation_id": None,
                "summary": item.get("name"),
                "parameters": [],
                "request_body": {},
                "security": security,
                "auth_required": auth_required,
                "tags": [],
                "sample_request": sample,
            })
        except Exception:
            continue
    return endpoints


def _parse_postman(content: bytes, doc: ApiDocument) -> tuple[list[dict], list[dict]]:
    try:
        text = content.decode("utf-8", errors="replace")
        data = json.loads(text)
    except Exception as exc:
        raise ParseError(f"Could not parse Postman JSON: {exc}") from exc

    # Top-level base URL from collection variables
    variables = {
        v.get("key", ""): v.get("value", "")
        for v in (data.get("variable") or [])
        if isinstance(v, dict)
    }
    base_url = variables.get("baseUrl") or variables.get("base_url") or variables.get("host")

    # Auth at collection level
    credentials: list[dict] = []
    col_auth = data.get("auth") or {}
    if isinstance(col_auth, dict) and col_auth.get("type") not in (None, "noauth"):
        auth_type = col_auth.get("type", "").lower()
        if auth_type == "bearer":
            bearer_list = col_auth.get("bearer", [])
            token = next(
                (x.get("value") for x in bearer_list if isinstance(x, dict) and x.get("key") == "token"),
                None,
            )
            if token:
                credentials.append({"scheme": "bearer", "name": "Authorization", "value": f"Bearer {token}", "label": "postman-collection-auth"})
        elif auth_type == "apikey":
            items_list = col_auth.get("apikey", [])
            key_name = next((x.get("value") for x in items_list if isinstance(x, dict) and x.get("key") == "key"), "X-API-Key")
            key_val = next((x.get("value") for x in items_list if isinstance(x, dict) and x.get("key") == "value"), "")
            if key_val:
                credentials.append({"scheme": "apikey", "name": key_name, "value": key_val, "label": "postman-collection-auth"})

    items = data.get("item") or []
    endpoints = _walk_postman_items(items, base_url)

    if not endpoints:
        raise ParseError("No requests found in Postman collection")
    return endpoints, credentials


# ── 3c Credentials file ───────────────────────────────────────────────────────

def _parse_credentials(content: bytes) -> list[dict]:
    text = content.decode("utf-8", errors="replace")
    credentials: list[dict] = []

    # Split into "blocks" on blank lines or obvious separators
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # curl command with -H / -b / --cookie
        if line.lower().startswith("curl ") or " curl " in line.lower():
            parsed = _parse_curl_line(line)
            credentials.extend(parsed)
            continue

        # Key: Value header lines
        m = re.match(r"^([\w\-]+)\s*:\s*(.+)$", line)
        if m:
            key, val = m.group(1).strip(), m.group(2).strip()
            key_lower = key.lower()
            if key_lower == "authorization":
                credentials.append({"scheme": _scheme_from_auth(val), "name": "Authorization", "value": val, "label": key})
            elif key_lower in ("x-api-key", "api-key", "api_key", "apikey"):
                credentials.append({"scheme": "apikey", "name": key, "value": val, "label": key})
            elif key_lower == "cookie":
                credentials.append({"scheme": "cookie", "name": "Cookie", "value": val, "label": "Cookie"})
            elif key_lower in ("bearer", "token", "access_token"):
                credentials.append({"scheme": "bearer", "name": "Authorization", "value": f"Bearer {val}", "label": key})
            continue

        # bare token / jwt (long, base64-ish string)
        if len(line) > 30 and re.match(r"^[A-Za-z0-9\-_\.]+$", line):
            # If it looks like a JWT (three base64 parts separated by dots)
            if line.count(".") == 2:
                credentials.append({"scheme": "bearer", "name": "Authorization", "value": f"Bearer {line}", "label": "jwt"})
            else:
                credentials.append({"scheme": "apikey", "name": "X-API-Key", "value": line, "label": "token"})

    return credentials


def _scheme_from_auth(value: str) -> str:
    lower = value.lower()
    if lower.startswith("bearer "):
        return "bearer"
    if lower.startswith("basic "):
        return "basic"
    if lower.startswith("apikey ") or lower.startswith("api-key "):
        return "apikey"
    return "bearer"


def _parse_curl_line(line: str) -> list[dict]:
    creds: list[dict] = []
    # Extract -H / --header values
    for m in re.finditer(r'-H\s+[\'"]([^\'"]+)[\'"]', line):
        header_line = m.group(1)
        colon_pos = header_line.find(":")
        if colon_pos < 0:
            continue
        hname = header_line[:colon_pos].strip()
        hval = header_line[colon_pos + 1:].strip()
        if hname.lower() == "authorization":
            creds.append({"scheme": _scheme_from_auth(hval), "name": "Authorization", "value": hval, "label": "curl-header"})
        elif hname.lower() in ("x-api-key", "api-key"):
            creds.append({"scheme": "apikey", "name": hname, "value": hval, "label": "curl-header"})
        elif hname.lower() == "cookie":
            creds.append({"scheme": "cookie", "name": "Cookie", "value": hval, "label": "curl-cookie"})
    # Extract -b / --cookie values
    for m in re.finditer(r'(?:-b|--cookie)\s+[\'"]([^\'"]+)[\'"]', line):
        creds.append({"scheme": "cookie", "name": "Cookie", "value": m.group(1), "label": "curl-cookie"})
    # Extract -u / --user basic auth
    for m in re.finditer(r'(?:-u|--user)\s+[\'"]([^\'"]+)[\'"]', line):
        creds.append({"scheme": "basic", "name": "Authorization", "value": f"Basic {m.group(1)}", "label": "curl-basic"})
    return creds


# ── 3d Free text / Confluence (LLM extraction) ────────────────────────────────

async def _parse_freetext(session: Session, content: bytes, doc: ApiDocument) -> list[dict]:
    try:
        from aespa.services.settings import get_llm_config
        from aespa.services import llm as llm_svc
    except ImportError:
        return []

    llm_cfg = get_llm_config(session)
    if llm_cfg is None:
        raise ParseError("No active LLM config — configure an LLM profile in settings first")

    text = content.decode("utf-8", errors="replace")[:_MAX_FREETEXT_LLM_CHARS]

    prompt = f"""You are an API analysis assistant. Extract all API endpoints from the following documentation.

Return a JSON array (and ONLY the JSON array, no prose). Each element should be an object with:
- "method": HTTP method (GET, POST, PUT, PATCH, DELETE, etc.)
- "path": URL path (e.g. /v1/users/{{id}})
- "summary": one-line description (or null)
- "auth_required": true/false (true if the endpoint requires authentication)
- "tags": array of tag strings (empty array if none)

Documentation:
---
{text}
---

JSON array of endpoints:"""

    try:
        raw = await llm_svc.plain_completion(llm_cfg, prompt)
    except Exception as exc:
        raise ParseError(f"LLM extraction failed: {exc}") from exc

    # Extract JSON array from the response
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        raise ParseError("LLM did not return a JSON array of endpoints")
    try:
        items = json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise ParseError(f"Could not parse LLM JSON response: {exc}") from exc

    endpoints = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not item.get("method") or not item.get("path"):
            continue
        endpoints.append({
            "method": item["method"].upper(),
            "path": item["path"],
            "summary": item.get("summary"),
            "auth_required": bool(item.get("auth_required", False)),
            "tags": item.get("tags", []),
        })

    if not endpoints:
        raise ParseError("LLM returned no endpoints")
    return endpoints


# ── 3e Source zip ─────────────────────────────────────────────────────────────

# Framework routing patterns — (regex for the file path, regex for route lines, method, path group)
_ROUTE_PATTERNS: list[tuple[str, str, str, int]] = [
    # FastAPI / Flask: @router.get("/path") / @app.route("/path", methods=["POST"])
    (r"\.(py)$", r'@(?:\w+\.)?(?:get|post|put|patch|delete|head)\(["\']([^"\']+)["\']', "FROM_DECORATOR", 1),
    (r"\.(py)$", r'@(?:\w+\.)?route\(["\']([^"\']+)["\'].*methods=\[["\'](.*?)["\']\]', "FROM_ROUTE", 1),
    # Express.js: router.get('/path', ...) / app.post('/path', ...)
    (r"\.(js|ts|mjs)$", r'(?:router|app)\.(get|post|put|patch|delete)\(["\`]([^"\'`]+)["\`]', "FROM_DECORATOR", 2),
    # Rails: get '/path', ... / resources :users
    (r"\.(rb)$", r'^\s*(get|post|put|patch|delete)\s+["\']([^"\']+)["\']', "FROM_DECORATOR", 2),
    # Laravel: Route::get('/path', ...)
    (r"\.(php)$", r'Route::(get|post|put|patch|delete)\(["\']([^"\']+)["\']', "FROM_DECORATOR", 2),
    # Spring: @GetMapping / @PostMapping / @RequestMapping
    (r"\.(java|kt)$", r'@(?:Get|Post|Put|Patch|Delete|Request)Mapping\(["\']([^"\']+)["\']', "FROM_DECORATOR", 1),
    # Go gin / echo: r.GET("/path", ...)
    (r"\.go$", r'\.(GET|POST|PUT|PATCH|DELETE)\(["\`]([^"\'`]+)["\`]', "FROM_DECORATOR", 2),
]


def _safe_unzip(zip_bytes: bytes) -> dict[str, bytes]:
    """Return {internal_path: bytes} after safety checks."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ParseError(f"Not a valid zip file: {exc}") from exc

    entries = zf.infolist()
    if len(entries) > _MAX_ZIP_ENTRIES:
        raise ParseError(f"Zip has {len(entries)} entries, exceeds limit of {_MAX_ZIP_ENTRIES}")

    total_bytes = 0
    files: dict[str, bytes] = {}
    for info in entries:
        name = info.filename
        # Path traversal guard: reject absolute paths, components with .., and NUL bytes
        if (
            name.startswith(("/", "\\"))
            or ".." in name.split("/")
            or ".." in name.split("\\")
            or "\x00" in name
        ):
            continue
        # Skip directories
        if name.endswith("/"):
            continue
        # Skip obviously non-code files (binaries, media, etc.)
        ext = Path(name).suffix.lower()
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".ttf", ".eot",
                   ".svg", ".mp4", ".mp3", ".pdf", ".exe", ".dll", ".so", ".dylib",
                   ".class", ".jar", ".war", ".ear", ".lock", ".sum"}:
            continue

        if info.file_size > _MAX_ZIP_SINGLE_BYTES:
            continue  # Skip oversized single files
        total_bytes += info.file_size
        if total_bytes > _MAX_ZIP_TOTAL_BYTES:
            break  # Stop before exceeding total limit

        try:
            files[name] = zf.read(name)
        except Exception:
            continue

    return files


def _parse_source_zip(content: bytes, doc: ApiDocument) -> list[dict]:
    files = _safe_unzip(content)
    if not files:
        raise ParseError("No readable source files found in zip")

    endpoints: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for file_path, file_bytes in files.items():
        # Only scan files with known extensions
        ext = Path(file_path).suffix.lower()
        if ext not in {".py", ".js", ".ts", ".mjs", ".rb", ".php", ".java", ".kt", ".go"}:
            continue

        try:
            source = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            continue

        for file_pattern, line_pattern, method_hint, path_group in _ROUTE_PATTERNS:
            if not re.search(file_pattern, file_path, re.IGNORECASE):
                continue
            for m in re.finditer(line_pattern, source, re.IGNORECASE | re.MULTILINE):
                if method_hint == "FROM_DECORATOR":
                    # The method may be the match group 0 prefix or the decorator name
                    method_part = m.group(0).split("(")[0].rsplit(".", 1)[-1].upper()
                    method_parts = {"ROUTE": "GET", "MAPPING": "GET", "REQUESTMAPPING": "GET"}
                    method = method_parts.get(method_part, method_part)
                    if method.lower() not in _HTTP_METHODS and method not in ("FROM_DECORATOR",):
                        # Try to infer from the decorator name
                        decorator = m.group(0).split("(")[0].upper()
                        for hm in _HTTP_METHODS:
                            if hm in decorator:
                                method = hm.upper()
                                break
                        else:
                            method = "GET"
                else:
                    method = "GET"

                try:
                    path = m.group(path_group).strip()
                except IndexError:
                    continue

                if not path.startswith("/"):
                    path = "/" + path
                key = (_norm_method(method), _norm_path(path))
                if key in seen:
                    continue
                seen.add(key)
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "summary": f"Discovered in {Path(file_path).name}",
                })

    if not endpoints:
        raise ParseError("No route definitions found in source zip")
    return endpoints


# ── Count helpers (used by router) ───────────────────────────────────────────

def count_endpoints(session: Session, collection_id: int) -> int:
    return len(
        list(
            session.exec(
                select(ApiEndpoint.id).where(ApiEndpoint.collection_id == collection_id)
            ).all()
        )
    )
