"""Service-layer storage + CRUD for API documentation uploads.

Raw bytes are written to disk under ``settings.data_dir``; only metadata is kept
in the DB. Stored filenames are generated (uuid) so the user-supplied filename is
never used to build a filesystem path (prevents path traversal).
"""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlmodel import Session, select

from aespa.config import get_settings
from aespa.models import ApiCollection, ApiDocument


# 25 MiB per-file cap for v1.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


class ApiDocumentServiceError(Exception):
    """Base class for service-layer errors."""


class ApiCollectionNotFound(ApiDocumentServiceError):
    pass


class ApiDocumentNotFound(ApiDocumentServiceError):
    pass


class UploadTooLarge(ApiDocumentServiceError):
    pass


class EmptyUpload(ApiDocumentServiceError):
    pass


def _storage_dir(collection_id: int) -> Path:
    base = Path(get_settings().data_dir) / "api_collections" / str(collection_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _sniff_doc_type(filename: str, content: bytes) -> str:
    """Best-effort classification of an uploaded document.

    Parsing happens in a later slice; this only assigns a display/type hint.
    """
    name = (filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""

    if ext == "zip" or content[:2] == b"PK":
        return "source_zip"

    # Peek at a decoded prefix for structured-doc markers.
    head = ""
    try:
        head = content[:4096].decode("utf-8", errors="ignore").lower()
    except Exception:
        head = ""

    if '"info"' in head and ('"_postman_id"' in head or "schema.getpostman.com" in head):
        return "postman"
    # openapi / swagger: match on content keywords first (extension is a hint, not a gate)
    if "openapi" in head:
        return "openapi"
    if "swagger" in head:
        return "swagger"
    if ext in {"yaml", "yml"}:
        return "openapi"
    # Everything else — markdown, txt, sql, html, json without openapi/swagger markers, etc.
    # The LLM will determine whether it contains endpoints, credentials, or both.
    if ext in {"md", "markdown", "txt", "html", "htm", "rst", "sql", "csv", "json"}:
        return "freetext"
    return "unknown"


def _require_collection(session: Session, collection_id: int) -> ApiCollection:
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise ApiCollectionNotFound(f"API collection id={collection_id} does not exist")
    return collection


def list_documents(session: Session, collection_id: int) -> list[ApiDocument]:
    _require_collection(session, collection_id)
    return list(
        session.exec(
            select(ApiDocument)
            .where(ApiDocument.collection_id == collection_id)
            .order_by(ApiDocument.created_at, ApiDocument.id)
        ).all()
    )


def get_document(session: Session, collection_id: int, document_id: int) -> ApiDocument:
    doc = session.get(ApiDocument, document_id)
    if doc is None or doc.collection_id != collection_id:
        raise ApiDocumentNotFound(
            f"API document id={document_id} does not exist in collection {collection_id}"
        )
    return doc


def create_document(
    session: Session,
    collection_id: int,
    *,
    filename: str,
    content: bytes,
    content_type: str | None = None,
    declared_type: str | None = None,
) -> ApiDocument:
    _require_collection(session, collection_id)

    if not content:
        raise EmptyUpload("Uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise UploadTooLarge(
            f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MiB upload limit"
        )

    safe_name = Path(filename or "upload").name or "upload"
    ext = ""
    if "." in safe_name:
        ext = "." + safe_name.rsplit(".", 1)[-1]
    stored_path = _storage_dir(collection_id) / f"{uuid.uuid4().hex}{ext}"
    stored_path.write_bytes(content)

    doc_type = declared_type or _sniff_doc_type(safe_name, content)

    doc = ApiDocument(
        collection_id=collection_id,
        filename=safe_name,
        doc_type=doc_type,
        content_type=content_type,
        stored_path=str(stored_path),
        size_bytes=len(content),
        status="uploaded",
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


def read_document_bytes(session: Session, collection_id: int, document_id: int) -> tuple[ApiDocument, bytes]:
    doc = get_document(session, collection_id, document_id)
    path = Path(doc.stored_path)
    if not path.is_file():
        raise ApiDocumentNotFound(f"Stored file for document id={document_id} is missing")
    return doc, path.read_bytes()


def delete_document(session: Session, collection_id: int, document_id: int) -> None:
    doc = get_document(session, collection_id, document_id)
    path = Path(doc.stored_path)
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
    session.delete(doc)
    session.commit()


def count_documents(session: Session, collection_id: int) -> int:
    return len(
        list(
            session.exec(
                select(ApiDocument.id).where(ApiDocument.collection_id == collection_id)
            ).all()
        )
    )
