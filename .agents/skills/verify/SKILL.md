---
name: verify
description: Drive a real local AESPA web UI and backend to check user journeys and retain browser and database evidence. Use after changing user-facing behavior.
---

# Verify AESPA

Run from the repository root. Read [features/README.md](features/README.md) and the feature recipe before driving. This uses the real FastAPI server, React UI, and a fresh SQLite database. It does not call an LLM or a target site for the site-creation recipe. Other journeys may do so; check their preconditions.

## Launch

Install dependencies once with `uv sync` and `npm ci --prefix frontend`, and install Chromium with `uv run playwright install chromium`. Use Node 24 or newer. Then:

```bash
node .agents/skills/verify/scripts/control.mjs launch
```

The helper starts `uv run --no-sync aespa` on a free loopback port with an empty directory under the system temporary directory (`node -p 'require("node:os").tmpdir()'`). AESPA runs migrations during startup and builds the frontend if needed. Launch prints the URL, PID, data directory, version, and evidence directory only after the UI, version endpoint, and sites API respond. The server log is in the evidence directory. The launch record is `aespa-verify-instance.json` in that temporary directory. This driver permits one verification instance at a time on this machine; never drive a server started by someone else or reuse an existing port.

## Doctor

```bash
node .agents/skills/verify/scripts/control.mjs doctor
```

Run this read-only check if anything looks wrong. It checks the recorded process, scratch directory, served UI, sites API, and version against `pyproject.toml`. A failed check means stop driving and inspect the retained `server.log`. It does not prove a scan target or LLM provider is ready.

## Drive

For the site setup journey:

```bash
node .agents/skills/verify/scripts/control.mjs drive-site
```

The helper uses Playwright selectors from `SiteForm.jsx` and `SitesList.jsx`. It opens the UI, fills the new site form, takes a before screenshot, submits, takes an after screenshot, reloads, and reads the saved record through the normal sites API. See the feature map for other journeys and their preconditions. A scan needs an authorized target and a configured LLM profile; do not start one merely to prove the UI loads.

## Evidence

The printed `aespa-verify-evidence/<run-id>/` directory in the system temporary directory survives cleanup. For site setup it contains `site-before-create.png`, `site-after-create.png`, `site-proof.json`, `instance.json`, and `server.log`. Preserve action and result evidence. For every new journey, exercise the real user path and confirm stored side effects after a reload or second read. Avoid internal setters and test-only endpoints. Only mock external systems at existing production boundaries, and state what the mock excludes. Check the effects of any dry run by observing writes and requests.

## Cleanup

```bash
node .agents/skills/verify/scripts/control.mjs cleanup
```

Run cleanup after success and after every failed attempt. It sends SIGTERM only to the recorded process group, removes only that run's scratch data, and retains the evidence directory. Confirm the proof files remain afterward. Do not kill processes by name or delete the evidence directory.
