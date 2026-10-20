# Set up a SAST scan

Users upload a source ZIP and run source analysis from the SAST page.

## Sub-features

- SAST-1: Open the new scan form and select a source.
- SAST-2: Start analysis and observe progress.
- SAST-3: Review saved leads and findings.

## How to get to it (user POV)

- Open **SAST**, then **New SAST Scan**.
- Reopen a scan from the SAST list.

## Driving it with Playwright

Preconditions: A safe sample source ZIP and a working LLM profile. The local instance starts without either. Set these up before SAST-2.

- SAST-1: Open `/#/sast-runs`, click **New SAST Scan**, select the ZIP through the source file input, and capture the selected filename.
- SAST-2: Submit the form, then observe `/#/sast-runs/{id}/progress`. Capture the submit action, progress state, and saved run from the normal SAST API.
- SAST-3: Open the run's leads and findings tabs. Capture the visible result and corresponding saved records.

## Gotchas

- The form starts the scan immediately after creating the run. Do not submit without a configured profile and an approved source ZIP.
- Empty leads may be a valid analysis result; judge it against the sample source and completed status.
