export const provider = {
  id: 1,
  name: "Fixture provider",
  api_format: "openai_compatible",
  base_url: "http://localhost:1234/v1",
  models: ["fixture-model"],
  has_api_key: true,
};
export const model = {
  id: 1,
  name: "Fixture model",
  provider_id: 1,
  provider_name: provider.name,
  model: "fixture-model",
  max_tokens: 1000,
  max_context_tokens: 32000,
  temperature: null,
};
export const profile = {
  id: 1,
  name: "Fixture profile",
  default_model_id: 1,
  default_model_name: model.name,
  role_models: {},
  is_active: true,
};
export const site = {
  id: 1,
  name: "Fixture site",
  base_url: "http://example.test",
  url: "http://example.test",
  scope_hosts: [],
  credentials: [],
  requires_auth: false,
};
export const collection = {
  id: 1,
  name: "Fixture API",
  base_url: "http://example.test",
  description: "Local browser fixture",
  scope_hosts: [],
  credentials: [],
};
export const run = {
  id: 1,
  site_id: 1,
  collection_id: 1,
  name: "Fixture run",
  status: "created",
  phase: "created",
  thinking_status: "idle",
  scope_hosts: [],
  per_user_progress: [],
  llm_profile_id: 1,
  coverage_mode: "track",
};
export const sast = {
  id: 1,
  name: "Fixture SAST",
  status: "pending",
  phase: "scope",
  llm_profile_id: 1,
  leads_count: 0,
  source_filename: "fixture.zip",
};
export const application = {
  id: 1,
  name: "Fixture application",
  description: "Local browser fixture",
};
export const campaign = {
  id: 1,
  application_id: 1,
  name: "Fixture campaign",
  status: "draft",
  source_members: [],
  target_members: [],
};

export async function installFixtures(page, { empty = false } = {}) {
  const writes = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (!path.startsWith("/api/")) return route.continue();
    if (request.method() !== "GET") {
      writes.push({ path, method: request.method(), body: request.postDataJSON() });
      return route.fulfill({ json: request.postDataJSON() || {} });
    }
    const tables = {
      "/api/version": { version: "fixture", username: "Local test" },
      "/api/settings/llm/providers": empty ? [] : [provider],
      "/api/settings/llm/model-configs": empty ? [] : [model],
      "/api/settings/llm/profiles": empty ? [] : [profile],
      "/api/sites": empty ? [] : [site],
      "/api/sites/1": site,
      "/api/sites/1/test-runs": empty ? [] : [run],
      "/api/api-collections": empty ? [] : [collection],
      "/api/api-collections/1": collection,
      "/api/api-collections/1/test-runs": empty ? [] : [run],
      "/api/test-runs/1": run,
      "/api/api-test-runs/1": run,
      "/api/test-runs/1/graph": { nodes: [], edges: [], links: [] },
      "/api/sast-runs": empty ? [] : [sast],
      "/api/sast-runs/1": sast,
      "/api/sast-runs/1/analysis": {
        phases: {},
        coverage: { files: [], summary: {} },
        work_program: {},
        assurance: {},
        report: {},
      },
      "/api/applications": empty ? [] : [application],
      "/api/applications/1": application,
      "/api/applications/1/campaigns": empty ? [] : [campaign],
      "/api/applications/1/campaigns/1": campaign,
      "/api/settings/llm/models": {},
    };
    if (path in tables) return route.fulfill({ json: tables[path] });
    if (path.endsWith("/events") || path.includes("/stream"))
      return route.fulfill({ contentType: "text/event-stream", body: ": fixture\n\n" });
    if (path.endsWith("/alice/sessions"))
      return route.fulfill({
        json: {
          chats: [{ id: "tab-default", title: "Session 1", messages: [] }],
          active_tab_id: "tab-default",
        },
      });
    if (path.endsWith("/status") || path.endsWith("/checkpoint"))
      return route.fulfill({ json: { running: false, status: "idle", resumable: false } });
    if (path.endsWith("/count")) return route.fulfill({ json: { count: 0 } });
    if (path.includes("/settings/"))
      return route.fulfill({
        json: {
          enabled: false,
          scope_hosts: [],
          max_steps: 20,
          panel_enabled: false,
          max_concurrent: 5,
        },
      });
    if (path.endsWith("/token-usage")) return route.fulfill({ json: {} });
    if (path.endsWith("/coverage"))
      return route.fulfill({ json: { cells: [], endpoints: [], pages: [], summary: {} } });
    return route.fulfill({ json: [] });
  });
  return { writes };
}
