import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { chromium } from "../frontend/node_modules/playwright/index.mjs";

const state = JSON.parse(readFileSync(path.join(tmpdir(), "aespa-verify-instance.json"), "utf8"));
async function api(url, options = {}) {
  const response = await fetch(`${state.url}${url}`, options);
  if (!response.ok) throw Error(`${response.status} ${await response.text()}`);
  return response.json();
}
const post = (url, body) => api(url, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
});
const base = "https://workflow-verification.test";
const site = (await api("/api/sites")).find(item => item.name === "Workflow index verification")
  || await post("/api/sites", { name: "Workflow index verification", base_url: base });
const run = await post(`/api/sites/${site.id}/test-runs`, { name: "Workflow index verification" });
const page = (key, label, url) => ({
  state_key: key, state_label: label, url: `${base}${url}`, title: label,
  state_kind: "interactive", status: "crawled", in_scope: true,
  takes_input: true, has_business_logic: true, req_auth: true,
  replay_steps_json: JSON.stringify({ root_url: `${base}/account`, steps: [
    { kind: "click", selector: "button", name: `Open ${label}` },
    { kind: "fill", selector: "[name=address]", name: "Address", value: "Test Street" },
  ] }),
});
const note = (id, name, status, extra = {}) => ({
  id, phase: "crawl_note", status, message: name,
  data_json: JSON.stringify({ note: { name, goal: `Reach ${name}`, start_url: `${base}/account`,
    status, reason: "Observed in the crawl", detail: status === "crawled" ? "Reached" : "Test data is missing",
    needs_input: status !== "crawled", ...extra } }),
});
const archive = {
  format: "aespa-crawl-export", version: 1, source: { site_base_url: `${base}/` },
  crawl: { pages: [page("address", "Address form", "/account"), page("checkout", "Checkout", "/checkout")],
    activity: { scan_log: [
      note(101, "Checkout", "crawled", { url: `${base}/checkout`, page_state_key: "checkout" }),
      note(102, "Payment setup", "needs_input", { request: "Supply a payment test method" }),
      note(103, "Address update", "needs_input"),
      note(104, "Address update", "crawled", { retry_of: 103, url: `${base}/account`, page_state_key: "address" }),
    ] } },
};
archive.crawl.pages.push(page("review", "Write review", "/reviews"));
const form = new FormData();
form.append("file", new Blob([JSON.stringify(archive)], { type: "application/json" }), "workflow-crawl.json");
await api(`/api/test-runs/${run.id}/crawl/import`, { method: "POST", body: form });
const browser = await chromium.launch({ headless: true });
const ui = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
ui.on("pageerror", error => errors.push(error.message));
try {
  await ui.goto(`${state.url}/#/runs/${run.id}/attack`);
  await ui.getByRole("tab", { name: "Workflows", exact: true }).click();
  const table = ui.locator(".workflow-coverage-table");
  await table.waitFor();
  const text = await table.innerText();
  for (const name of ["Checkout", "Payment setup", "Address update", "Write review"]) assert(text.includes(name), text);
  assert.match(text, /Crawl/i);
  await ui.reload();
  await table.waitFor();
  const coverage = await api(`/api/test-runs/${run.id}/workflow-coverage`);
  assert(coverage.workflows.some(workflow => workflow.name === "Payment setup"));
  const notes = await api(`/api/test-runs/${run.id}/crawl/workflows`);
  const waiting = notes.notes.filter(item => item.needs_input);
  assert.deepEqual(waiting.map(item => item.name), ["Payment setup"]);
  await ui.screenshot({ path: path.join(state.evidenceDir, "workflow-index.png") });
  const needsInput = ui.getByRole("button", { name: /needs input/i });
  await needsInput.click();
  const notifications = ui.locator(".workflow-notification");
  await notifications.first().waitFor();
  assert.equal(await notifications.count(), 1);
  assert.match(await notifications.innerText(), /Payment setup/);
  await ui.screenshot({ path: path.join(state.evidenceDir, "workflow-notifications.png") });
  assert.deepEqual(errors, []);
  writeFileSync(path.join(state.evidenceDir, "workflow-index-proof.json"), JSON.stringify({ runId: run.id, coverage, waiting, browserErrors: errors }, null, 2));
  console.log(JSON.stringify({ runId: run.id, evidenceDir: state.evidenceDir, workflows: coverage.workflows.length, notifications: waiting.length }));
} finally {
  await browser.close();
}
