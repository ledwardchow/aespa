# Advanced Auth Implementation Plan

**Date**: 2026-05-31  
**Status**: ✅ Complete

## Problem

The current `_authenticate()` function in `crawler.py` assumes a simple single-page login flow (username → password → submit). It fails for:

- **Entra / SAML / SSO**: Multi-step flows with redirects, intermediate pages, tenant selection
- **TOTP 2FA**: Google Authenticator, Authy — OTP prompt appears after password submit
- **MS Authenticator push / SMS OTP / FIDO2/YubiKey**: Cannot be automated; require human interaction
- **Magic links**: Email-based auth, no password field at all

## Solution: Three New Auth Strategies

Per-credential `auth_mode` field dispatches to one of four paths:

| Mode | How it works | Covers |
|------|-------------|--------|
| `auto` | Existing single-page Playwright automation (default) | Simple username/password forms |
| `totp` | Auto-login + detects MFA prompt + fills TOTP code from seed | Google Authenticator, Authy, any TOTP |
| `seed` | Skips browser entirely — parses pasted cURL or cookies/headers into ScannerSession | Any session exported from DevTools |
| `guided` | Opens a headed (non-headless) Chromium window; user logs in manually; UI "I'm Done" button captures session | Entra, SAML, MS Authenticator push, FIDO2/YubiKey, magic links — anything |

---

## Implementation Phases

### Phase 1 — Data Model ✅ TODO

**Files**: `src/aespa/models.py`, `src/aespa/schemas.py`

- [x] Added `AuthMode` enum: `auto | totp | seed | guided`
- [x] Added fields to `Credential`: `auth_mode`, `totp_seed`, `seed_cookies_json`, `seed_headers_json`
- [x] Existing rows default to `auto` (no migration work)
- [x] Updated `CredentialIn`, `CredentialOut` schemas

---

### Phase 2 — Session Seed ✅ Done

**Files**: `src/aespa/services/crawler.py`

- [x] `parse_curl_command(curl_text) -> (cookies, headers)` — parses `-H` and `-b`/`--cookie` flags from raw cURL string
- [x] `_authenticate_seed(page, credential)` — injects stored cookies/headers into headless context, reloads page
- [x] Wired into auth dispatch

---

### Phase 3 — TOTP ✅ Done

**Files**: `pyproject.toml`, `src/aespa/services/crawler.py`

- [x] Added `pyotp>=2.9.0` dependency
- [x] `_detect_mfa_prompt(page) -> bool` — detects OTP input after form submit
- [x] `_fill_totp_if_prompted(page, cred)` — generates `pyotp.TOTP(seed).now()` and fills + submits
- [x] `_authenticate_totp` = `_authenticate_auto` + `_fill_totp_if_prompted`

---

### Phase 4 — Guided Login ✅ Done

**Files**: `src/aespa/services/crawler.py`, `src/aespa/api/scan.py`

- [x] `_guided_registry: dict[int, asyncio.Event]` — module-level, keyed by `credential_id`
- [x] `_authenticate_guided(page, login_url, cred, run_id)` — launches headed Chromium, emits SSE, waits on event, injects cookies into headless context
- [x] Display check (`sys.platform == "darwin"` / `$DISPLAY` / `$WAYLAND_DISPLAY`) — clear error on headless with `seed` fallback suggestion
- [x] `GET  /api/test-runs/{run_id}/guided-login/status`
- [x] `POST /api/test-runs/{run_id}/guided-login/{credential_id}/confirm`

---

### Phase 5 — API & Schema ✅ Done

**Files**: `src/aespa/services/sites.py`

- [x] `create_site`, `update_site`, `add_credential` pass `auth_mode`, `totp_seed`, `seed_cookies_json`, `seed_headers_json` through to the `Credential` model
- [x] `totp_seed` intentionally excluded from `CredentialOut` (write-only)

---

### Phase 6 — UI ✅ Done

**Files**: `src/aespa/web/app.js`

- [x] Auth mode dropdown (`auto / totp / seed / guided`) in credential edit form
- [x] TOTP mode: TOTP seed input field
- [x] Seed mode: cURL paste textarea (auto-parses on blur) + editable Cookies JSON + Extra Headers JSON fields
- [x] Guided mode: inline info banner in credential form explaining the workflow
- [x] Run detail page: `guidedLoginPending` state, SSE handlers, prominent "I'm Done" panel that appears during crawl

---

## Decisions

- **MS Authenticator push, SMS, FIDO2**: intentionally not automated — `guided` is the correct UX answer
- **Existing credentials**: `auth_mode` defaults to `auto`, zero migration work
- **Headless degraded mode**: `guided` in headless env gives clear error + prompts `seed`
- **`totp_seed` security**: excluded from read responses; stored alongside other creds (same plaintext-acceptable local pentesting model)

---

## Progress Log

| Date | Phase | Notes |
|------|-------|-------|
| 2026-05-31 | Planning | Initial plan created |
| 2026-05-31 | All phases | Implementation complete — 28 tests passing |
