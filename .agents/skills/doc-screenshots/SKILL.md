---
name: doc-screenshots
description: Automated documentation screenshot capture and refresh utility for AESPA web and API interfaces.
---

# Documentation Screenshot Capture Skill

Use this skill when documentation screenshots need to be updated or refreshed across the AESPA application.

## Prerequisites

- Local AESPA backend server running at `http://127.0.0.1:8000` (`uv run aespa`).
- Playwright Chromium installed (`uv run playwright install chromium`).

## Execution Command

Run the capture script directly using `uv`:

```bash
uv run python scripts/capture_doc_screenshots.py
```

### Optional Arguments

- `--url`: Base URL of the AESPA server (default: `http://127.0.0.1:8000`)
- `--out-dir`: Directory where screenshots are saved (default: `docs/images`)
- `--db-path`: SQLite database path to query for top runs (default: `aespa.db`)

Example custom invocation:

```bash
uv run python scripts/capture_doc_screenshots.py --out-dir docs/images_preview --url http://127.0.0.1:8000
```

## Captured Documentation Images

The script automatically selects the web run and API run with the highest finding and traffic count from `aespa.db`, and generates:

- `sites.png` (`/#/`)
- `sitesetup.png` (`/#/sites/new`)
- `testruns.png` (`/#/sites/{site_id}`)
- `editrun.png` (`/#/sites/{site_id}/runs/new`)
- `agentstatus.png` & `runlanding.png` (`/#/runs/{web_run_id}` Status tab with ALICE collapsed)
- `sitemap.png` (`/#/runs/{web_run_id}` Site Map tab)
- `attacksurface.png` (`/#/runs/{web_run_id}` Attack Surface tab)
- `findings.png` & `webfindings.png` (`/#/runs/{web_run_id}` Findings tab)
- `trafficlog.png` (`/#/runs/{web_run_id}` Traffic Log tab)
- `sastleads.png` (`/#/runs/{web_run_id}` SAST Leads tab)
- `alice.png` (`/#/runs/{web_run_id}` Status tab with ALICE expanded to full height)
- `apis.png` & `apisetup.png` (`/#/apis`)
- `apispecparsed.png` (`/#/apis/{collection_id}`)
- `apifindings.png` (`/#/api-runs/{api_run_id}` Findings tab)
- `apiworkprogram.png` (`/#/api-runs/{api_run_id}` OWASP Coverage tab)
