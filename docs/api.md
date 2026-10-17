# AESPA API

The API extension lets CI pipelines and other tools create Sites, run web and SAST scans, follow their progress, and read the results. The full definition, with every field, is on **Extensions → API → Settings** under **API definition**. Download the OpenAPI file there for Postman, Insomnia, or a client generator. Each endpoint there also has example `curl` calls, using your AESPA address, and example responses; the OpenAPI file includes the same request examples.

## Set up

1. Open **Extensions** and enable **API**.
2. Open the API extension's **Settings** and create a token. Choose what it may do:
   - **SAST scans** (`sast`)
   - **Web scans** (`web`)
   - **Create and change Sites** (`sites`)
3. Copy the token. AESPA shows it only once.

Send the token with every request:

```bash
curl -H "Authorization: Bearer $AESPA_TOKEN" http://127.0.0.1:8000/extension/aespa.api/v1/scans
```

### Reaching AESPA from another machine

AESPA has no login, and its own `/api` routes are open to anyone who can reach it. Tokens protect only this API. To let a CI runner reach AESPA, publish just `/extension/aespa.api/v1/` through a reverse proxy or tunnel, and keep everything else private. Token management refuses requests that come from another machine or carry proxy forwarding headers, so manage tokens in AESPA on its own computer.

A token sees only the scans it created. Any token with the `sites` permission can read and change every Site.

## SAST scan from a ZIP file

```bash
BASE=http://127.0.0.1:8000/extension/aespa.api/v1

curl -sf -X POST "$BASE/sast/scans" \
  -H "Authorization: Bearer $AESPA_TOKEN" \
  -H "Idempotency-Key: $CI_PIPELINE_ID" \
  -F file=@source.zip \
  -F analysis_mode=deep
```

The response is the scan's status. Its `id` looks like `sast-17`.

To use a source extension instead of a file, such as GitHub repository:

```bash
curl -sf -X POST "$BASE/sast/scans/from-source" \
  -H "Authorization: Bearer $AESPA_TOKEN" -H "Content-Type: application/json" \
  -d '{"provider_id": "aespa.githubrepository", "parameters": {"repository": "acme/shop", "ref": "main"}}'
```

## Web scan

Send `site_id` for an existing Site, or describe the Site in `site`. Creating a Site needs the `sites` permission.

```bash
curl -sf -X POST "$BASE/web/scans" \
  -H "Authorization: Bearer $AESPA_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "site": {
      "name": "Shop staging",
      "base_url": "https://staging.shop.example",
      "requires_auth": true,
      "login_url": "https://staging.shop.example/login",
      "scope_hosts": ["api.staging.shop.example"],
      "scan_guidance": "Do not submit real payments.",
      "credentials": [
        {"label": "Admin", "username": "admin@example.com", "password": "..."},
        {"label": "2FA user", "auth_mode": "totp", "username": "u2", "password": "...", "totp_seed": "JBSWY3DPEHPK3PXP"}
      ]
    },
    "update_site": true,
    "max_pages": 200,
    "coverage_mode": "standard"
  }'
```

- By default the crawl starts at once and the dynamic scan follows when the crawl succeeds. Set `scan_after_crawl` to `false` to crawl only, then call `POST /web/scans/{scan_id}/scan` later.
- `update_site: true` replaces the Site with the same name. Without it, a name that already exists returns `409`.
- Passwords, TOTP seeds, and sensitive login field values are never returned.
- Accounts with `auth_mode: "guided"` need a person to sign in at the AESPA browser window. They are rejected unless you set `unattended: false`. When AESPA is waiting for a person, the scan's state is `needs_action`.

If a scan is created but cannot start, for example because no LLM is configured, the error includes its `scan_id`. Fix the problem and call `POST /scans/{scan_id}/start`.

## Following a scan

```bash
curl -s "$BASE/scans/sast-17" -H "Authorization: Bearer $AESPA_TOKEN"
```

| Field | Meaning |
| --- | --- |
| `state` | `queued`, `preparing`, `running`, `needs_action`, `paused`, `completed`, `failed`, or `stopped` |
| `phase` | Web: `crawling`, `scanning`, `reviewing`, `crawled`, `finished`. SAST: `preparing_source`, `analyzing`, `finished` |
| `percent` | Share of planned tests done, or `null` when AESPA cannot measure it |
| `resumable` | SAST only: `true` when the scan can be resumed from its saved progress |
| `message`, `error`, `needs_action` | What is happening, why it failed, or what a person must do |
| `counts.findings` | Findings so far by severity |

`completed`, `failed`, and `stopped` are final. To avoid tight polling loops, add `?wait=30` and the previous response's `ETag` as `If-None-Match`. AESPA holds the request until the status changes or 30 seconds pass, and returns `304` if nothing changed.

`GET /scans/{scan_id}/activity?after=<next_cursor>` returns the activity log. `POST /scans/{scan_id}/stop` stops a scan.

A SAST scan can pause, for example when the LLM provider hits a rate limit. When its `resumable` field is `true`, `POST /sast/scans/{scan_id}/resume` continues it from its saved progress. `POST /scans/{scan_id}/start` starts it over from the beginning instead.

## LLM profiles

A scan profile chooses the LLM models AESPA uses. Scans use the active profile unless you send `llm_profile_id` when creating them.

```bash
curl -s "$BASE/llm-profiles" -H "Authorization: Bearer $AESPA_TOKEN"
```

Each profile has an `id`, a `name`, whether it is `active`, and its `default_model`. Any token can list profiles. Profiles are created and changed in AESPA under **Settings**.

## Results

| Route | Returns |
| --- | --- |
| `GET /scans/{scan_id}/findings` | Findings, most severe first. Filter with `severity=high,critical`. Add `include_dismissed=true` for false positives. |
| `GET /scans/{scan_id}/summary?fail_on=high` | Counts by severity and category, and `gate.passed`: false when any finding is at or above `fail_on` |
| `GET /scans/{scan_id}/sarif` | Web or SAST results as SARIF 2.1.0, for GitHub code scanning and other tools. Web results have one rule per OWASP category and use the affected URL as the location. Findings marked false positive are left out; add `include_dismissed=true` to include them as suppressed results. SAST results include reportable findings only. |

Results are available while a scan runs, marked `partial: true`.

## Callbacks

Add `callbacks` when creating a scan (for an upload, send it as a JSON form field), or set a default callback URL on the token.

```json
"callbacks": {
  "url": "https://ci.example.com/aespa-events",
  "events": ["scan.started", "scan.needs_action", "scan.completed", "scan.failed", "scan.stopped"]
}
```

Events: `scan.started`, `scan.phase_changed`, `scan.progress` (at most once a minute; not sent unless listed), `scan.needs_action`, `scan.paused`, `scan.completed`, `scan.failed`, `scan.stopped`. Every scan sends `scan.started` first. The body contains the event, a delivery ID, and the scan's status with links; fetch findings with your token.

If you do not send a `secret`, AESPA uses the token's callback secret or creates one and returns it once in `callbacks.secret`. Check each request:

```python
import hashlib, hmac, time

def verify(secret: str, header: str, body: bytes) -> bool:
    parts = dict(item.split("=", 1) for item in header.split(","))
    if abs(time.time() - int(parts["t"])) > 300:
        return False
    expected = hmac.new(secret.encode(), f"{parts['t']}.".encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, parts["v1"])
```

Respond with any `2xx` status within 10 seconds. Other responses, timeouts, and redirects are retried after 30 seconds, then 2, 5, 15, and 30 minutes, then marked failed. `GET /scans/{scan_id}/deliveries` lists attempts, and `POST /deliveries/{id}/redeliver` sends one again. Failed callbacks also appear on the settings page. Turn off **Send callbacks** in the extension settings to pause sending.

## Retrying safely

Send an `Idempotency-Key` header on create requests. Repeating the request with the same key within 24 hours returns the first response instead of starting another scan. Reusing a key for a different request returns `422`.

## GitHub Actions example

```yaml
- name: AESPA SAST scan
  timeout-minutes: 120   # a paused or needs_action scan never reaches a final state on its own
  env:
    AESPA_URL: ${{ secrets.AESPA_URL }}   # https://aespa.example.com/extension/aespa.api/v1
    AESPA_TOKEN: ${{ secrets.AESPA_TOKEN }}
  run: |
    git archive --format=zip -o source.zip HEAD
    SCAN=$(curl -sf -X POST "$AESPA_URL/sast/scans" \
      -H "Authorization: Bearer $AESPA_TOKEN" \
      -H "Idempotency-Key: ${{ github.run_id }}-${{ github.run_attempt }}" \
      -F file=@source.zip | jq -r .id)
    while :; do
      STATE=$(curl -sf "$AESPA_URL/scans/$SCAN?wait=30" -H "Authorization: Bearer $AESPA_TOKEN" | jq -r .state)
      case "$STATE" in completed|failed|stopped) break ;; esac
    done
    curl -sf "$AESPA_URL/scans/$SCAN/sarif" -H "Authorization: Bearer $AESPA_TOKEN" -o aespa.sarif
    curl -sf "$AESPA_URL/scans/$SCAN/summary?fail_on=high" -H "Authorization: Bearer $AESPA_TOKEN" \
      | jq -e '.gate.passed'

- uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: aespa.sarif
```

## Versioning

Paths start with `/v1`. Fields may be added to v1 responses; existing fields are not renamed or removed. A breaking change would use a new `/v2` path.
