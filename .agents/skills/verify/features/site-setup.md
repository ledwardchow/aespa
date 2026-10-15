# Set up a site

Users save a web target before they configure or start a test run.

## Sub-features

- SITE-1: Create a site with name and base URL.
- SITE-2: Reopen the site after a browser reload.
- SITE-3: Edit or delete a saved site.

## How to get to it (user POV)

- Open **Sites** in the sidebar, then **New site**.
- Open a saved site from the Sites list.

## Driving it with Playwright

Preconditions: A fresh AESPA instance with no configured sites. The example URL is saved only; this journey does not crawl it.

- SITE-1 and SITE-2: Run `node .agents/skills/verify/scripts/control.mjs drive-site`. It clicks **New site**, fills **Name** and **Base URL**, clicks **Create site**, reloads the detail page, and checks `GET /api/sites` for the saved name and URL. Keep both screenshots and `site-proof.json`.
- SITE-3: From the saved detail page use the visible **Edit** action, change the name, save, reload, and read `GET /api/sites/{id}`. For delete, use the Sites list **Delete** action, accept the confirmation, then check that the item is absent from the list. Capture each action and result separately.

## Gotchas

- The create script covers SITE-1 and SITE-2 only. SITE-3 needs a separate browser drive.
- Saving a base URL does not prove that a crawl can reach that target.
- The site list may have two **New site** buttons when empty; the script uses the first visible match.
