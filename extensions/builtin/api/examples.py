"""Example request bodies and responses published in the OpenAPI definition.

Values are made up. Keep them valid against the request models; a test sends
every request example through validation.
"""

from __future__ import annotations

_SITE = {
    "name": "Shop staging",
    "base_url": "https://staging.shop.example",
    "requires_auth": True,
    "login_url": "https://staging.shop.example/login",
    "scope_hosts": ["api.staging.shop.example"],
    "scan_guidance": "Do not submit real payments.",
    "credentials": [
        {"label": "Admin", "username": "admin@shop.example", "password": "change-me"},
        {
            "label": "Two-factor user",
            "auth_mode": "totp",
            "username": "mfa@shop.example",
            "password": "change-me",
            "totp_seed": "JBSWY3DPEHPK3PXP",
        },
    ],
}

SITE = {
    "basic": {
        "summary": "Public site",
        "value": {"name": "Docs site", "base_url": "https://docs.shop.example"},
    },
    "signed_in": {"summary": "Site with accounts", "value": _SITE},
    "custom_login": {
        "summary": "Custom login form and workflow",
        "value": {
            "name": "Partner portal",
            "base_url": "https://partners.shop.example",
            "requires_auth": True,
            "login_url": "https://partners.shop.example/sign-in",
            "credentials": [
                {
                    "label": "Partner",
                    "login_fields": [
                        {"key": "company", "label": "Company code", "value": "ACME"},
                        {"key": "email", "label": "Email", "value": "ops@acme.example"},
                        {
                            "key": "password",
                            "label": "Password",
                            "value": "change-me",
                            "sensitive": True,
                        },
                    ],
                }
            ],
            "workflow_data": [
                {
                    "name": "Place order",
                    "goal": "Submit a purchase order",
                    "start_url": "https://partners.shop.example/orders/new",
                    "instructions": "Add one item, then submit the order.",
                }
            ],
        },
    },
}

CREDENTIAL = {
    "password": {
        "summary": "Username and password",
        "value": {
            "label": "Viewer",
            "username": "viewer@shop.example",
            "password": "change-me",
        },
    },
    "email_code": {
        "summary": "Email sign-in code",
        "value": {
            "label": "Email code user",
            "auth_mode": "email_otp",
            "username": "otp@shop.example",
            "password": "change-me",
            "test_mailbox_url": "https://mail.shop.example/inbox/otp",
        },
    },
}

WEB_SCAN = {
    "existing_site": {
        "summary": "Scan an existing Site",
        "value": {"site_id": 12, "coverage_mode": "standard", "max_pages": 200},
    },
    "new_site": {
        "summary": "Create or update a Site and scan it",
        "value": {
            "site": _SITE,
            "update_site": True,
            "name": "Nightly scan",
            "max_pages": 200,
            "coverage_mode": "standard",
            "callbacks": {"url": "https://ci.shop.example/aespa-events"},
        },
    },
    "crawl_only": {
        "summary": "Crawl now, scan later",
        "value": {"site_id": 12, "scan_after_crawl": False},
    },
}

SOURCE_SCAN = {
    "github": {
        "summary": "GitHub repository",
        "value": {
            "provider_id": "aespa.githubrepository",
            "parameters": {"repository": "acme/shop", "ref": "main"},
            "analysis_mode": "deep",
            "callbacks": {
                "url": "https://ci.shop.example/aespa-events",
                "events": ["scan.completed", "scan.failed"],
            },
        },
    },
}

START_SCAN = {
    "mode": {"summary": "Choose the scan depth", "value": {"coverage_mode": "deep"}},
}

SCAN_STATUS = {
    "id": "web-42",
    "kind": "web",
    "name": "Nightly scan",
    "state": "running",
    "phase": "scanning",
    "status": "running",
    "outcome": None,
    "percent": 38,
    "message": "Testing pages",
    "counts": {
        "findings": {"critical": 0, "high": 1, "medium": 3, "low": 2, "info": 0},
        "pages": 143,
        "max_pages": 200,
    },
    "needs_action": None,
    "error": None,
    "site_id": 12,
    "scan_after_crawl": True,
    "created_at": "2026-10-16T09:00:00+00:00",
    "started_at": "2026-10-16T09:00:02+00:00",
    "finished_at": None,
    "links": {
        "self": "/extension/aespa.api/v1/scans/web-42",
        "findings": "/extension/aespa.api/v1/scans/web-42/findings",
        "summary": "/extension/aespa.api/v1/scans/web-42/summary",
        "activity": "/extension/aespa.api/v1/scans/web-42/activity",
        "sarif": "/extension/aespa.api/v1/scans/web-42/sarif",
    },
    "callbacks": {
        "url": "https://ci.shop.example/aespa-events",
        "events": ["scan.started", "scan.completed", "scan.failed"],
        "secret": None,
    },
}

SAST_SCAN_STATUS = {
    **SCAN_STATUS,
    "id": "sast-17",
    "kind": "sast",
    "name": "acme/shop main",
    "phase": "analyzing",
    "status": "scanning",
    "percent": 54,
    "message": "Reviewing the code",
    "counts": {
        "findings": {"critical": 0, "high": 2, "medium": 1, "low": 0, "info": 0}
    },
    "site_id": None,
    "scan_after_crawl": None,
    "links": {
        "self": "/extension/aespa.api/v1/scans/sast-17",
        "findings": "/extension/aespa.api/v1/scans/sast-17/findings",
        "summary": "/extension/aespa.api/v1/scans/sast-17/summary",
        "activity": "/extension/aespa.api/v1/scans/sast-17/activity",
        "sarif": "/extension/aespa.api/v1/scans/sast-17/sarif",
    },
    "callbacks": None,
}


def created(example: dict) -> dict:
    """A 201 response entry that shows ``example`` for this route only."""
    return {201: {"content": {"application/json": {"example": example}}}}
