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
export const system = {
  id: 1,
  name: "Fixture system",
  description: "Local browser fixture",
};
export const campaign = {
  id: 1,
  system_id: 1,
  name: "Fixture campaign",
  status: "draft",
  source_members: [],
  target_members: [],
};

export async function installFixtures(page, { empty = false } = {}) {
  const writes = [];
  const sastBenchmarkingExtension = {
    id: "aespa.benchmarking",
    name: "Benchmark Lab",
    author: "aespa",
    version: "1.0.0",
    aespa_api: "1",
    capabilities: ["api.routes"],
    enabled: false,
    status: "disabled",
    settings: {},
    settings_fields: [],
    source_providers: [],
    web_scanners: [],
  };
  await page.route("**/extension/aespa.benchmarking/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const tables = {
      "/extension/aespa.benchmarking/targets": {
        sites: [
          {
            id: 1,
            name: site.name,
            dataset: {
              id: 1,
              name: "Fixture ground truth",
              item_count: 2,
            },
            runs: [
              {
                id: 1,
                name: "Fixture scan",
                status: "complete",
                default_evaluation_model: { id: 1, name: "Fixture model" },
              },
            ],
          },
        ],
        apis: [{ id: 1, name: collection.name, dataset: null, runs: [] }],
        sast_runs: [{ id: 1, name: sast.name, status: "completed" }],
      },
      "/extension/aespa.benchmarking/datasets": [
        { id: 1, name: "Fixture ground truth", item_count: 2 },
      ],
      "/extension/aespa.benchmarking/results": [
        {
          id: 1,
          run_kind: "site",
          run_id: 1,
          target_kind: "site",
          target_id: 1,
          run_name: "Fixture scan",
          scan_cost_usd: 0.42,
          comparison: { method: "model", model: { id: 1, name: "Fixture model" } },
          scan_models: {
            test_lead: { id: 1, name: "Fixture Test Lead", model: "fixture-model" },
            sast: [],
          },
          created_at: "2026-09-27T00:00:00Z",
          summary: { full: 1, partial: 0, missing: 1 },
          ground_truth: {
            name: "Fixture ground truth",
            items: [
              { external_id: "GT-1", title: "SQL injection" },
              { external_id: "GT-2", title: "Missing audit logs" },
            ],
          },
          findings: [{ id: 4, reference: "SITE-004", title: "SQL injection" }],
          rows: [
            { external_id: "GT-1", disposition: "full", finding_ids: [4], reason: "Matched" },
            { external_id: "GT-2", disposition: "missing", finding_ids: [], reason: "No match" },
          ],
        },
      ],
      "/extension/aespa.benchmarking/evaluations": [],
    };
    return route.fulfill({ json: tables[path] || [] });
  });
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    if (!path.startsWith("/api/")) return route.continue();
    if (request.method() !== "GET") {
      writes.push({ path, method: request.method(), body: request.postDataJSON() });
      if (path === "/api/extensions/aespa.benchmarking/enabled") {
        sastBenchmarkingExtension.enabled = request.postDataJSON()?.enabled ?? false;
        sastBenchmarkingExtension.status = sastBenchmarkingExtension.enabled
          ? "loaded"
          : "disabled";
        return route.fulfill({ json: sastBenchmarkingExtension });
      }
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
      "/api/systems": empty ? [] : [system],
      "/api/systems/1": system,
      "/api/systems/1/campaigns": empty ? [] : [campaign],
      "/api/systems/1/campaigns/1": campaign,
      "/api/settings/llm/models": {},
      "/api/settings/browser-debug": {
        browser_engine: "playwright_chromium",
        browser_visible: false,
        graphical_display_available: true,
        graphical_display_message: null,
      },
      "/api/settings/reporting-debug": {
        capture_enabled: false,
        panel_enabled: false,
      },
      "/api/settings/cloudflare-access": { audience: null },
      "/api/extensions": [sastBenchmarkingExtension],
      "/api/settings/code-execution": {
        enabled: true,
        image_ref: "ledwardchow/aespa-python-executor:0.1",
        allowed_roles: ["alice", "specialist", "test_lead"],
        timeout_s: 30,
        memory_mb: 256,
        cpu_cores: 0.5,
        pids_limit: 32,
        workspace_mb: 16,
        output_limit_bytes: 65536,
        artifact_limit_bytes: 10485760,
        max_requests_per_execution: 20,
        max_concurrent_requests: 5,
        max_concurrent_executions: 2,
        retain_redacted_source: true,
      },
      "/api/settings/code-execution/status": {
        available: false,
        docker_installed: true,
        docker_available: false,
        image_present: false,
        message:
          "Docker is installed, but its service is not running or cannot be reached. Start Docker and try again.",
      },
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
