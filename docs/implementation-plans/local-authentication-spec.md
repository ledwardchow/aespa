# Local authentication specification

Date: 2026-10-17

Status: Proposed. This document describes planned behaviour, not implemented functionality. Keep this plan untracked. Do not stage or commit it.

## User experience

AESPA requires authentication for its management interface and core API. Users do not need accounts or passwords. AESPA generates an authentication key that users can copy from the console or view in Settings.

Use **Authentication key** consistently in the interface. Keep this key separate from the API extension's tokens for other apps.

### Console launch

- Show the authentication key beside the listening address in the startup display, where AESPA currently shows its listening message.
- Keep the address and key readable and copyable in both the interactive console and plain terminal output.
- Show **Press ~ to open AESPA in your browser** in the interactive console.
- Accept both tilde and the unshifted backtick key for the browser shortcut.
- Pressing tilde opens the default browser at the actual listening address and selected port. The opened page authenticates automatically.
- The shortcut works from normal console views without submitting or changing a setting. While a text field is being edited, preserve normal text entry.
- Repeated presses can open new tabs and must still work after a port change. Each automatic login uses a fresh, short-lived, single-use login link.
- On a machine without a graphical browser, keep the console running and show the address and key for manual use.

### Browser login

- An unauthenticated visit to the normal app address shows a sign-in screen with an **Authentication key** field and a **Sign in** button.
- Tell the user that the key is shown in the AESPA console on startup.
- A valid key signs the browser in and opens AESPA. An invalid key shows a plain error and allows another attempt.
- Remember authentication with a persistent HttpOnly session cookie. Do not store the authentication key in browser local storage.
- Revisiting the same address, refreshing, opening another tab, or restarting the browser loads AESPA without another prompt while the session remains valid.
- Keep valid sessions across backend restarts. This requires persistent session verification state as well as a persistent authentication key.
- If the session expires, is revoked, or is missing, return to the key-entry screen. Clearing browser cookies also requires signing in again.
- Preserve a requested internal page through sign-in. Redirect only to local AESPA paths.
- Cookies do not isolate services by port. Keep sessions separate between AESPA instances and test that a cookie from another local service or AESPA instance cannot authenticate a request.
- Do not promise that a session carries between `localhost`, `127.0.0.1`, different browser profiles, or native webviews. Use a consistent address in launchers.

### Settings

- Add **Authentication key** to the console's Settings menu. Opening it shows the key, browser shortcut, and instructions for returning to Settings.
- Add an **Authentication key** option to Settings.
- Mask the value initially. Provide explicit **Show** and **Copy** actions.
- Require an authenticated management session to retrieve the key. Return it only on an explicit request with caching disabled.
- Explain that the key grants access to AESPA settings and scan data. Explain that integrations use tokens from the API extension's settings instead.

### macOS and Windows desktop apps

- Both launchers use the same backend authentication as console launches.
- On launch, obtain a short-lived, single-use login link through the launcher process and open it in the native webview.
- Reopening a hidden window preserves its session. If the backend has restarted or the session is invalid, the launcher can create a fresh login link through its trusted local channel.
- Never expose an unauthenticated HTTP endpoint that returns a key or generates usable login links.

### Docker

- Make the address and authentication key available in startup console output. Document how to obtain them with container logs.
- Persist the key and session verification state in the existing data volume so container restarts do not require another browser login.
- Support a protected key file or Docker secret for unattended deployments. Do not bake a key into an image or commit one to source control.
- Default the management port mapping to `127.0.0.1:8000:8000`. The server may continue listening on `0.0.0.0` inside the container.
- If the published host port differs from the container port, the user-facing login instructions must use the host address and port.

## Authentication rules

Apply authentication according to the route's purpose. Do not exempt every extension route or require a browser session for the integration API.

| Routes | Required authentication |
| --- | --- |
| Core `/api/` routes | AESPA management session. Allow only explicitly listed minimal startup and sign-in endpoints without a session. |
| Ordinary extension routes | AESPA management session by default. |
| `/extension/aespa.api/v1/` integration operations | Existing API extension bearer token, permissions, and scan-access checks. No management session or second key required. |
| `/extension/aespa.api/admin/` routes | AESPA management session plus the existing local-request restrictions. An integration token cannot manage tokens. |
| Settings and extension administration | AESPA management session. |
| Management WebSockets and event streams | AESPA management session, checked before accepting or streaming. |

The integration API's OpenAPI document is currently public. Keep that exception explicit and limited to the definition. It must contain no credentials or private runtime data. Management copies of extension definitions remain authenticated.

Integration tokens must never unlock the core API, ordinary extensions, the authentication-key display, or token administration. Browser login must not bypass the integration API's existing token permissions or scan ownership rules.

Keep host validation, browser-origin checks, and CSRF protection for cookie-authenticated changes. Browser-only checks must not reject normal non-browser bearer-token clients for lacking an Origin header. Configure allowed external hostnames explicitly when using a reverse proxy.

## Optional integration listener

Keep the existing single-port deployment supported. Add an optional separate integration listener for deployments that need access from other machines.

- The management listener serves the UI, core API, ordinary extensions, and administration. It binds to loopback by default.
- The integration listener serves only the API extension's public `/v1/` operations and its explicit OpenAPI definition. It requires the existing bearer tokens for operations.
- Do not mount the main app, Settings, token administration, or other extension routes on the integration listener.
- Disabling the API extension removes access on both listeners.
- Both listeners use the same backend process and extension state. Do not start duplicate scan schedulers or callback workers.
- Disable the separate integration listener inside Docker, even when a port is configured. Docker continues serving the bearer-token API on its normal port.
- Remote access uses HTTPS through a configured proxy or tunnel. Proxy traffic never gains management access merely because its connection appears local.

The separate listener is optional and enabled with `AESPA_INTEGRATION_PORT`. Its listening address is set with `AESPA_INTEGRATION_HOST`, which defaults to loopback.

## Key and session handling

- Generate a cryptographically random authentication key on first startup and retain it in protected local storage. Restrict access to the operating-system user running AESPA where supported.
- Use a separate random browser session credential. Do not send the management key with every browser request.
- Set persistent cookies with HttpOnly and an appropriate SameSite policy. Require Secure cookies for HTTPS deployments and explicitly support local HTTP operation.
- Give sessions a documented expiry. The exact duration remains an implementation decision.
- Changing the authentication key invalidates existing management sessions and unused login links. It does not rotate API extension tokens.
- Rate-limit failed sign-in attempts. Never include submitted keys in errors or request logs.
- Automatic login links use single-use secrets rather than the persistent authentication key. Remove the secret from the address after exchange and prevent caching, referrer leakage, and access-log disclosure.
- Displaying the key in startup output is intentional. Do not copy it into scan logs, activity logs, reports, diagnostics, or telemetry. Users with access to the terminal or container logs can obtain management access.

## Acceptance checks

1. Console startup shows the actual address, selected port, authentication key, and tilde shortcut.
2. Tilde opens an authenticated browser session, including after a port change and on repeated presses.
3. A new browser profile visiting the app sees the key-entry screen. An incorrect key fails and the correct key succeeds.
4. Refreshing, revisiting the normal URL, restarting the browser, and restarting AESPA preserve a valid login.
5. Missing, expired, or revoked sessions show sign-in without exposing settings, scan data, or extension administration.
6. Settings can reveal and copy the key only after management authentication. Unauthenticated requests cannot retrieve it.
7. macOS and Windows launch directly into authenticated native windows. Reopening a hidden window still works.
8. Docker retains authentication state through restarts and binds the management port to host loopback by default.
9. Existing integration requests work with their current bearer tokens and no browser session. Invalid, deactivated, and insufficiently scoped tokens still fail.
10. Integration tokens cannot access management routes. Token administration requires the management session and retains local-request restrictions.
11. Ordinary extension routes, WebSockets, and event streams reject unauthenticated management access.
12. The optional integration listener cannot serve the UI, core API, administration, or another extension. Disabling the API extension blocks its integration routes.
13. Cross-site browser requests and unexpected hostnames fail without blocking configured integration clients.
14. Credentials from another AESPA instance do not authenticate this instance. Startup output is the only intentional routine log disclosure of the management key.
