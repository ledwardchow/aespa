"""Extension discovery, diagnostics, and settings."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from aespa.extensions import get_extension_manager

router = APIRouter(prefix="/api/extensions", tags=["extensions"])


class ExtensionSettingsUpdate(BaseModel):
    settings: dict[str, Any]


class ExtensionEnabledUpdate(BaseModel):
    enabled: bool


async def _extension_payload(
    extension_id: str, *, live_check: bool = False
) -> dict[str, Any]:
    manager = get_extension_manager()
    manager.ensure_loaded()
    record = manager.extensions.get(extension_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Extension not found")
    payload = manager.extension_dict(record)
    providers = [
        registered
        for registered in manager.source_providers.values()
        if registered.extension_id == extension_id
    ]
    scanners = [
        registered
        for registered in manager.web_scanners.values()
        if registered.extension_id == extension_id
    ]
    availability = await asyncio.gather(
        *[
            item.provider.check_availability(manager.context_for(extension_id))
            for item in providers
        ],
        return_exceptions=True,
    )
    payload["source_providers"] = []
    payload["web_scanners"] = []
    for registered, state in zip(providers, availability, strict=True):
        descriptor = registered.provider.descriptor
        if isinstance(state, Exception):
            state_payload = {
                "available": False,
                "status": "error",
                "message": str(state),
                "details": {},
            }
        else:
            state_payload = {
                "available": state.available,
                "status": state.status,
                "message": state.message,
                "details": state.details,
            }
        payload["source_providers"].append(
            {
                "id": descriptor.id,
                "label": descriptor.label,
                "description": descriptor.description,
                "request_fields": [
                    field.__dict__ for field in descriptor.request_fields
                ],
                "availability": state_payload,
            }
        )
    scanner_availability = await asyncio.gather(
        *[
            (
                item.scanner.check_connection(manager.context_for(extension_id))
                if live_check and hasattr(item.scanner, "check_connection")
                else item.scanner.check_availability(manager.context_for(extension_id))
            )
            for item in scanners
        ],
        return_exceptions=True,
    )
    for registered, state in zip(scanners, scanner_availability, strict=True):
        payload["web_scanners"].append(
            {
                "id": registered.scanner.id,
                "label": registered.scanner.label,
                "description": registered.scanner.description,
                "availability": (
                    {
                        "available": False,
                        "status": "error",
                        "message": str(state),
                        "details": {},
                    }
                    if isinstance(state, Exception)
                    else {
                        "available": state.available,
                        "status": state.status,
                        "message": state.message,
                        "details": state.details,
                    }
                ),
            }
        )
    return payload


@router.get("")
async def list_extensions() -> list[dict[str, Any]]:
    manager = get_extension_manager()
    manager.ensure_loaded()
    return await asyncio.gather(
        *[_extension_payload(extension_id) for extension_id in manager.extensions]
    )


@router.get("/source-providers")
async def list_source_providers() -> list[dict[str, Any]]:
    extensions = await list_extensions()
    return [
        {
            **provider,
            "extension_id": extension["id"],
            "extension_name": extension["name"],
        }
        for extension in extensions
        for provider in extension["source_providers"]
    ]


@router.get("/{extension_id}")
async def get_extension(extension_id: str) -> dict[str, Any]:
    return await _extension_payload(extension_id)


@router.put("/{extension_id}/enabled")
async def update_extension_enabled(
    extension_id: str, payload: ExtensionEnabledUpdate
) -> dict[str, Any]:
    manager = get_extension_manager()
    manager.ensure_loaded()
    try:
        manager.set_enabled(extension_id, payload.enabled)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Extension not found") from exc
    return await _extension_payload(extension_id)


@router.patch("/{extension_id}/settings")
async def update_extension_settings(
    extension_id: str, payload: ExtensionSettingsUpdate
) -> dict[str, Any]:
    manager = get_extension_manager()
    manager.ensure_loaded()
    try:
        manager.save_settings(extension_id, payload.settings)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Extension not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _extension_payload(extension_id)


@router.post("/{extension_id}/check")
async def check_extension(extension_id: str) -> dict[str, Any]:
    return await _extension_payload(extension_id, live_check=True)
