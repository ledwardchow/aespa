"""TLS verification settings for outbound httpx clients."""

from __future__ import annotations

import os
import ssl


def httpx_verify(ca_bundle: str | None, default: bool) -> ssl.SSLContext | bool:
    """Return an httpx ``verify`` value for an optional saved CA bundle.

    httpx no longer accepts a CA bundle path directly, so build the same SSL
    context it used to create from one: a directory is loaded as ``capath``,
    anything else as ``cafile``. Without a bundle, ``default`` decides whether
    certificates are checked.
    """
    if not ca_bundle:
        return default
    if os.path.isdir(ca_bundle):
        return ssl.create_default_context(capath=ca_bundle)
    return ssl.create_default_context(cafile=ca_bundle)
