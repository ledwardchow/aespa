# Set up an API collection

Users save an API target before uploading its documents and creating a test run.

## Sub-features

- API-1: Create a collection with a name and base URL.
- API-2: Reopen the collection after a reload.
- API-3: Upload API documents and inspect parsed endpoints.

## How to get to it (user POV)

- Open **APIs** in the sidebar, then **New API collection**.
- Open a saved collection from the APIs list.

## Driving it with Playwright

Preconditions: A fresh AESPA instance. API-3 needs a known OpenAPI document and its expected endpoint list.

- API-1: Open `/#/apis`, click **New API collection**, fill `input[placeholder="e.g. Payments API"]` and `input[placeholder="https://api.example.com"]`, then click **Create collection**. Capture the filled form and resulting detail page.
- API-2: Reload the detail page and check the saved collection through `GET /api/api-collections`.
- API-3: Use the document upload control on the collection detail page. Wait for parsing to finish, then check the visible endpoints against `GET /api/api-collections/{id}/endpoints` and the supplied document. Capture the upload action and parsed result.

## Gotchas

- A collection can be saved without contacting its base URL.
- API-3 has no seed document in this verification skill. Report it as unverified if none is supplied; do not replace it with a mocked endpoint list.
