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

test("provider form conversion preserves zero limits and custom models", () => {
  const form = providerToForm({
    name: "Local",
    api_format: "openai_compatible",
    max_tpm: 0,
    max_rpm: 0,
  });
  expect(
    providerPayload({ ...form, models: " a, b\nc ", base_url: " http://localhost:1234/v1 " }),
  ).toMatchObject({
    models: ["a", "b", "c"],
    base_url: "http://localhost:1234/v1",
    max_tpm: 0,
    max_rpm: 0,
  });
  expect(providerPayload({ ...form, models: "" }).models).toEqual([]);
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
  });
  expect(llmPayload(form)).toMatchObject({
    provider_id: 4,
    temperature: 0,
    max_tokens: 200,
    max_context_tokens: 32000,
  });
  expect(llmPayload({ ...form, use_temperature: false, max_context_auto: true })).toMatchObject({
    temperature: null,
    max_context_tokens: null,
  });
});

test("new profiles choose a predictable first model without mutating the provider", () => {
  const provider = { id: 1, name: "Example", models: ["z", "a"] };
  expect(llmProfileToForm(null, [provider])).toMatchObject({
    provider_id: 1,
    model: "a",
    name: "Example/a",
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
  expect(
    scanProfileToForm({ name: "Example", default_model_id: 4, role_models: { crawler: 2 } }),
  ).toMatchObject({ default_model_id: "4", role_models: { crawler: "2", alice: "" } });
});
