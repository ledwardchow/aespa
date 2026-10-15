# Configure an LLM provider

Users configure a provider and profile before starting scans.

## Sub-features

- LLM-1: Open provider settings and create a provider.
- LLM-2: Create a profile that selects a provider and model.
- LLM-3: Reopen and edit saved settings.

## How to get to it (user POV)

- Open **LLM Configuration**, then **Providers** or **Profiles**.
- Direct routes are `/#/settings/providers` and `/#/settings/profiles`.

## Driving it with Playwright

Preconditions: A disposable provider or local model endpoint. Never enter a real secret in evidence screenshots or transcripts.

- LLM-1: Open `/#/settings/providers`, click the visible new-provider action, fill the provider form, save, and check the provider list after reload.
- LLM-2: Open `/#/settings/profiles`, create a profile using that provider and a known model, save, and check the list after reload.
- LLM-3: Open the saved provider or profile, use **Edit**, save a changed display name, and verify the persisted value through the normal settings API.

## Gotchas

- A saved provider or profile does not prove the credentials or model work. A live provider check requires an available external service.
- Do not store API keys in proof artifacts.
