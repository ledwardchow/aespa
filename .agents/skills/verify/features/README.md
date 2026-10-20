# AESPA verification map

This is the maintained list of user journeys. Start with the real local instance described in `../SKILL.md`. The site setup journey has a scripted driver; the other recipes give exact UI paths and observable results but have not yet been automated.

## Baseline

- Use the fresh data directory created by `control.mjs launch`.
- Run `control.mjs doctor` before a journey if the instance looks wrong.
- Keep proof in the run's printed `aespa-verify-evidence/<run-id>/` directory under the system temporary directory.
- Do not start a crawl, scan, or source upload without its stated preconditions.
- Record each entry point tested. A skipped entry point is still unverified.

## Features

- [Set up a site](site-setup.md) - create and reopen a web target.
- [Set up an API collection](api-collection.md) - create and reopen an API target.
- [Set up a SAST scan](sast-scan.md) - upload source and start analysis.
- [Configure an LLM provider](llm-settings.md) - prepare a provider and profile for scans.
