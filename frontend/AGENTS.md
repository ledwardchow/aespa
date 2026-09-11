# Frontend work

Read README.md here for the source layout and commands. Run npm commands in this directory.

- Keep route composition in src/app, feature behavior in src/features, and reusable behavior in src/shared.
- Do not import another feature's private modules. Expose a small public.js integration when necessary. Shared code cannot import app or features.
- Move a component's local state and handlers with its JSX. Keep saved data separate from editable drafts.
- Preserve existing URLs, browser storage keys, run-kind isolation, and chat replay behavior.
- Do not edit ../src/aespa/web directly; npm run build generates it.
- Run npm run check and affected browser checks for substantive UI changes. Browser tests use fixtures and must not call live providers or start scans.
- Browser tests (`npm run test:e2e` or direct Playwright commands) and Vite dev/preview servers need loopback access. In a sandbox that restricts local ports, request access on the first invocation, including for the browser test process when a server is already running. Do not wait for a bind error or connection timeout before requesting it. See ../AGENTS.md under Sandbox Execution Notes. `npm run check` does not run browser tests and does not need loopback access by default.
- Inspect desktop and narrow layouts after CSS changes. Check nested tab bounds against their actual parent.
- Use TypeScript for new shared contracts. Existing JavaScript can be converted incrementally; do not suppress type errors with broad any types.
