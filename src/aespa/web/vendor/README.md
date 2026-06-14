# Vendored frontend libraries

These are the runtime dependencies for the web UI, bundled as native ES modules
and committed to the repo so the app loads with **zero external network
dependency** (works offline / airgapped, no reliance on a third-party CDN).

They are referenced by the importmap in [`../index.html`](../index.html) and
imported by [`../app.js`](../app.js) via bare specifiers (`react`, `d3`, etc.).

| File | Package | Notes |
|---|---|---|
| `react.js` | `react@18.3.1` | zero imports |
| `react-dom-client.js` | `react-dom@18.3.1/client` | imports the bare `react` specifier so it shares the single React instance (do **not** inline a second copy, or React breaks at runtime) |
| `htm.js` | `htm@3.1.1` | zero imports |
| `d3.js` | `d3@7.9.0` | all ~30 submodules inlined, zero imports |

These files are immutable and pinned by version. There is **no build step** —
they are served directly as static files.

## Updating a version

Re-fetch the matching bundle from esm.sh (replace `<ver>` with the new version):

```sh
curl -sL "https://esm.sh/react@<ver>/es2022/react.bundle.mjs"        -o react.js
curl -sL "https://esm.sh/htm@<ver>/es2022/htm.bundle.mjs"            -o htm.js
curl -sL "https://esm.sh/d3@<ver>/es2022/d3.bundle.mjs"              -o d3.js
curl -sL "https://esm.sh/react-dom@<ver>/X-ZXJlYWN0/es2022/client.bundle.mjs" -o react-dom-client.js
```

Notes:
- The `X-ZXJlYWN0` path segment is esm.sh's encoding of `?external=react`. It is
  what keeps `react-dom` importing the bare `react` specifier (resolved by the
  importmap to `react.js`) instead of inlining its own copy of React.
- After updating, bump the package version (the importmap appends `?v=` from
  `settings.app_version`) so the service worker and browsers fetch the new files.
- Verify nothing points back at the CDN: the only `esm.sh` mention in each file
  should be the comment banner on line 1.
