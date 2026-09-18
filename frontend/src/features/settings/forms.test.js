import { expect, test } from "vitest";
import { providerToForm, providerPayload } from "./providerForm.js";
import { llmProfileToForm, llmPayload } from "./modelForm.js";
import { burpRestApiToForm, burpRestApiPayload } from "./burpForm.js";
import { scanProfileToForm } from "./scanProfileForm.js";

test("editing a provider keeps a stored key unless explicitly changed or cleared", () => {
  const form = providerToForm({
    name: "Example",
    api_format: "openai_compatible",
    has_api_key: true,
    models: ["example-model"],
  });
  expect(form.api_key).toBe("");
  expect(providerPayload(form).api_key).toBeNull();
  expect(providerPayload({ ...form, api_key: " new-key " }).api_key).toBe("new-key");
  expect(providerPayload({ ...form, clear_api_key: true }).api_key).toBe("");
});

test("provider form conversion preserves custom models", () => {
  const form = providerToForm({
    name: "Local",
    api_format: "openai_compatible",
  });
  expect(
    providerPayload({ ...form, models: " a, b\nc ", base_url: " http://localhost:1234/v1 " }),
  ).toMatchObject({
    models: ["a", "b", "c"],
    base_url: "http://localhost:1234/v1",
  });
  expect(providerPayload({ ...form, models: "" }).models).toEqual([]);
});

test("Vertex AI providers use ADC project and location without key settings", () => {
  const form = providerToForm({
    name: "Vertex",
    api_format: "google_vertex",
    project_id: "example-project",
    location: "us-central1",
    models: ["gemini-2.5-flash"],
    has_api_key: true,
    base_url: "https://unused.example",
  });

  expect(providerPayload(form)).toMatchObject({
    api_key: "",
    base_url: null,
    project_id: "example-project",
    location: "us-central1",
    models: ["gemini-2.5-flash"],
  });
});

test("model edits preserve explicit temperature zero and manual context size", () => {
  const form = llmProfileToForm({
    name: "Example",
    provider_id: 4,
    model: "model",
    temperature: 0,
    max_tokens: 200,
    max_context_tokens: 32000,
    context_limit_source: "manual",
    max_tpm: 120000,
    max_rpm: 60,
  });
  expect(llmPayload(form)).toMatchObject({
    provider_id: 4,
    temperature: 0,
    max_tokens: 200,
    max_context_tokens: 32000,
    max_tpm: 120000,
    max_rpm: 60,
  });
  expect(llmPayload({ ...form, use_temperature: false, max_context_auto: true })).toMatchObject({
    temperature: null,
    max_context_tokens: null,
    detected_context_tokens: null,
  });
});

test("auto context preserves a freshly discovered limit without making it manual", () => {
  const payload = llmPayload({
    ...llmProfileToForm(null, [{ id: 1, name: "Provider", models: ["model"] }]),
    name: "Provider/model",
    max_context_tokens: 1000000,
    detected_context_tokens: 1000000,
  });

  expect(payload).toMatchObject({
    max_context_tokens: null,
    detected_context_tokens: 1000000,
  });
});

test("new profiles choose a predictable first model without mutating the provider", () => {
  const provider = { id: 1, name: "Example", models: ["z", "a"] };
  expect(llmProfileToForm(null, [provider])).toMatchObject({
    provider_id: 1,
    model: "a",
    name: "Example/a",
    max_tokens: 16384,
  });
  expect(provider.models).toEqual(["z", "a"]);
});

test("integration forms preserve key keep/replace/clear semantics", () => {
  const form = burpRestApiToForm({ enabled: false, has_api_key: true });
  expect(burpRestApiPayload(form).api_key).toBeNull();
  expect(burpRestApiPayload({ ...form, api_key: " new-key " }).api_key).toBe("new-key");
  expect(burpRestApiPayload({ ...form, clear_api_key: true }).api_key).toBe("");
});

test("scan profile drafts retain role selections as select values", () => {
  const models = [
    { id: 2, provider_id: 10 },
    { id: 4, provider_id: 20 },
  ];
  expect(
    scanProfileToForm(
      { name: "Example", default_model_id: 4, role_models: { crawler: 2 } },
      models,
    ),
  ).toMatchObject({
    default_model_id: "4",
    default_provider_id: "20",
    role_models: { crawler: "2", alice: "" },
    role_providers: { crawler: "10", alice: "" },
  });
});
