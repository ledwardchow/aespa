from __future__ import annotations

import threading

from aespa.extensions import (
    ExtensionOpenAPI,
    SourceProviderField,
    get_extension_manager,
)

from . import callbacks, models
from .router import build_router
from .scans import EXTENSION_ID
from .webhooks import build_webhooks

API_VERSION = "1.0.0"
SETTINGS = [
    SourceProviderField(
        key="send_callbacks",
        label="Send callbacks",
        type="boolean",
        default=True,
        help=(
            "Send scan events to callback URLs. When off, nothing is sent; when "
            "turned back on, each scan's latest change is sent."
        ),
    ),
]
DESCRIPTION = """\
Create Sites, start web and SAST scans, follow their progress, and read results.

**Authentication.** Send `Authorization: Bearer <token>`. Create tokens on the
API extension's settings page in AESPA. Each token has scopes: `sast` for SAST
scans, `web` for web scans, and `sites` to create or change Sites. A token sees
only the scans it created. Any `sites` token can read and change every Site.

**Scan IDs** look like `web-42` or `sast-17`.

**Following a scan.** Poll `GET /v1/scans/{scan_id}` (use `wait` and
`If-None-Match` to avoid tight loops), or set `callbacks` when you create the
scan and AESPA will POST signed events to your URL.

**Access.** AESPA has no login of its own and its main `/api` routes are open to
anyone who can reach it. Tokens protect this API when you publish only
`/extension/aespa.api/v1/` through a reverse proxy or tunnel. Token management
is only available from AESPA on the same computer.
"""


class ApiExtension:
    def register(self, registry) -> None:
        registry.register_settings_fields(SETTINGS)
        store = registry.data_store(models.metadata)
        core = registry.core
        registry.register_api_router(
            build_router(store, core),
            openapi=ExtensionOpenAPI(
                title="AESPA API",
                version=API_VERSION,
                description=DESCRIPTION,
                webhooks=build_webhooks(),
            ),
        )
        changed = callbacks.ChangedRuns()
        core.on_run_change(changed.add)
        threading.Thread(
            target=callbacks.run_worker,
            args=(
                store,
                core,
                changed,
                threading.Event(),
                lambda: get_extension_manager().data_stores.get(EXTENSION_ID) is store,
                lambda: (
                    get_extension_manager()
                    .get_settings(EXTENSION_ID)
                    .get("send_callbacks", True)
                ),
            ),
            name="aespa-api-callbacks",
            daemon=True,
        ).start()


def create_extension():
    return ApiExtension()
