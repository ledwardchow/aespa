#!/usr/bin/env node
import { spawn } from "node:child_process";
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../../../frontend/node_modules/playwright/index.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const statePath = path.join(tmpdir(), "aespa-verify-instance.json");
const command = process.argv[2];
const readState = () => JSON.parse(readFileSync(statePath, "utf8"));
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const version = readFileSync(path.join(root, "pyproject.toml"), "utf8").match(/^version = "([^"]+)"/m)?.[1];

async function freePort() {
  const server = createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}

async function doctor(state) {
  process.kill(state.pid, 0);
  const expectedDir = path.join(tmpdir(), `aespa-verify-${state.id}`);
  if (state.dataDir !== expectedDir || !existsSync(state.dataDir)) throw Error("Unexpected data directory");
  const [v, sites, page] = await Promise.all([
    fetch(`${state.url}/api/version`),
    fetch(`${state.url}/api/sites`),
    fetch(state.url),
  ]);
  if (!v.ok || !sites.ok || !page.ok) throw Error("AESPA is not ready");
  const actual = (await v.json()).version;
  if (actual !== version) throw Error(`Wrong AESPA version: ${actual}, expected ${version}`);
  if (!(await page.text()).includes("AESPA")) throw Error("UI is not available");
  console.log(JSON.stringify({ url: state.url, pid: state.pid, dataDir: state.dataDir, version: actual }));
}

async function launch() {
  if (existsSync(statePath)) throw Error(`An instance record exists at ${statePath}. Run doctor or cleanup first.`);
  const id = `${Date.now()}-${process.pid}`;
  const dataDir = path.join(tmpdir(), `aespa-verify-${id}`);
  const evidenceDir = path.join(tmpdir(), "aespa-verify-evidence", id);
  mkdirSync(dataDir);
  mkdirSync(evidenceDir, { recursive: true });
  const port = await freePort();
  const log = openSync(path.join(evidenceDir, "server.log"), "a");
  const child = spawn("uv", ["run", "--no-sync", "aespa"], {
    cwd: root,
    env: { ...process.env, AESPA_HOST: "127.0.0.1", AESPA_PORT: String(port), AESPA_DATA_DIR: dataDir, AESPA_DATABASE_URL: `sqlite:///${dataDir}/aespa.db` },
    detached: true,
    stdio: ["ignore", log, log],
  });
  closeSync(log);
  const state = { id, pid: child.pid, url: `http://127.0.0.1:${port}`, dataDir, evidenceDir };
  writeFileSync(statePath, JSON.stringify(state, null, 2));
  writeFileSync(path.join(evidenceDir, "instance.json"), JSON.stringify(state, null, 2));
  for (let attempt = 0; attempt < 90; attempt++) {
    try { await doctor(state); console.log(`Evidence: ${evidenceDir}`); return; } catch { await sleep(1000); }
  }
  throw Error(`Startup did not become usable. See ${path.join(evidenceDir, "server.log")}; run cleanup.`);
}

async function driveSite() {
  const state = readState();
  await doctor(state);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const name = `Verification site ${state.id}`;
  const observations = [];
  try {
    await page.goto(`${state.url}/#/`);
    await page.getByRole("button", { name: "New site" }).first().click();
    await page.locator('input[placeholder="e.g. Juice Shop"]').fill(name);
    await page.locator('input[placeholder="https://target.example.com"]').fill("https://example.test");
    await page.screenshot({ path: path.join(state.evidenceDir, "site-before-create.png") });
    observations.push({ action: "Fill new site form", url: page.url(), name });
    await page.getByRole("button", { name: "Create site" }).click();
    await page.waitForURL(/#\/sites\/\d+$/);
    await page.locator(".topbar-title").filter({ hasText: name }).waitFor();
    await page.screenshot({ path: path.join(state.evidenceDir, "site-after-create.png") });
    observations.push({ action: "Create site", url: page.url(), title: await page.locator(".topbar-title").innerText() });
    await page.reload();
    await page.locator(".topbar-title").filter({ hasText: name }).waitFor();
    const sites = await (await fetch(`${state.url}/api/sites`)).json();
    const stored = sites.find((site) => site.name === name && site.base_url === "https://example.test/");
    if (!stored) throw Error("Created site was not stored");
    observations.push({ action: "Reload and read saved site", site: stored });
    writeFileSync(path.join(state.evidenceDir, "site-proof.json"), JSON.stringify(observations, null, 2));
    console.log(`Site creation verified. Evidence: ${state.evidenceDir}`);
  } finally { await browser.close(); }
}

function cleanup() {
  const state = readState();
  if (state.dataDir !== path.join(tmpdir(), `aespa-verify-${state.id}`)) throw Error("Refusing to remove unexpected directory");
  try { process.kill(-state.pid, "SIGTERM"); } catch (error) { if (error.code !== "ESRCH") throw error; }
  rmSync(state.dataDir, { recursive: true, force: true });
  rmSync(statePath);
  console.log(`Instance stopped. Evidence retained: ${state.evidenceDir}`);
}

try {
  if (command === "launch") await launch();
  else if (command === "doctor") await doctor(readState());
  else if (command === "drive-site") await driveSite();
  else if (command === "cleanup") cleanup();
  else throw Error("Use launch, doctor, drive-site, or cleanup");
} catch (error) { console.error(error); process.exitCode = 1; }
