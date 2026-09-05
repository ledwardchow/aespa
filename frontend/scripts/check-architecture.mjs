import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "@babel/parser";

const root = fileURLToPath(new URL("../src/", import.meta.url));
const walk = (directory) =>
  fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(file) : [file];
  });
const files = walk(root).filter((file) => /\.[jt]sx?$/.test(file));
const graph = new Map();
const errors = [];
const label = (file) => path.relative(root, file);
function resolve(from, source) {
  const base = path.resolve(path.dirname(from), source);
  return [base, ...[".js", ".jsx", ".ts", ".tsx", "/index.js"].map((ext) => base + ext)].find(
    (candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile(),
  );
}
function sources(node, result = []) {
  if (!node || typeof node !== "object") return result;
  if (
    ["ImportDeclaration", "ExportNamedDeclaration", "ExportAllDeclaration"].includes(node.type) &&
    node.source
  )
    result.push(node.source.value);
  if (node.type === "ImportExpression" && node.source.type === "StringLiteral")
    result.push(node.source.value);
  if (node.type === "CallExpression" && node.callee.type === "Import")
    result.push(node.arguments[0].value);
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) value.forEach((item) => sources(item, result));
    else if (value && typeof value === "object") sources(value, result);
  }
  return result;
}
for (const file of files) {
  const imports = sources(
    parse(fs.readFileSync(file, "utf8"), { sourceType: "module", plugins: ["jsx", "typescript"] }),
  );
  const dependencies = [];
  for (const source of imports.filter((source) => source?.startsWith("."))) {
    const target = resolve(file, source);
    if (!target) {
      errors.push(`${label(file)}: missing ${source}`);
      continue;
    }
    if (label(file).startsWith("shared/") && /^(features|app)\//.test(label(target)))
      errors.push(
        `${label(file)} imports ${label(target)}: shared code cannot depend on features or app`,
      );
    const owner = label(file).match(/^features\/([^/]+)/)?.[1];
    const targetOwner = label(target).match(/^features\/([^/]+)/)?.[1];
    if (owner && targetOwner && owner !== targetOwner && !label(target).endsWith("/public.js")) {
      errors.push(`${label(file)} imports private feature module ${label(target)}`);
    }
    if (/\.[jt]sx?$/.test(target)) dependencies.push(target);
  }
  graph.set(file, dependencies);
}
const visited = new Set();
const stack = [];
function visit(file) {
  if (stack.includes(file)) {
    errors.push(
      `Import cycle: ${[...stack.slice(stack.indexOf(file)), file].map(label).join(" -> ")}`,
    );
    return;
  }
  if (visited.has(file)) return;
  visited.add(file);
  stack.push(file);
  for (const dependency of graph.get(file) || []) visit(dependency);
  stack.pop();
}
for (const file of graph.keys()) visit(file);
if (process.argv.includes("--inventory")) {
  const reachable = new Set();
  const mark = (file) => {
    if (reachable.has(file)) return;
    reachable.add(file);
    (graph.get(file) || []).forEach(mark);
  };
  mark(path.join(root, "main.jsx"));
  console.log("Modules not reachable from main.jsx (review tests and types separately):");
  console.log(
    files
      .filter((file) => !reachable.has(file))
      .map(label)
      .join("\n"),
  );
  console.log("\nCross-feature dependencies:");
  for (const [file, deps] of graph)
    for (const dep of deps) {
      const from = label(file).match(/^features\/([^/]+)/)?.[1];
      const to = label(dep).match(/^features\/([^/]+)/)?.[1];
      if (from && to && from !== to) console.log(`${label(file)} -> ${label(dep)}`);
    }
}
if (errors.length) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else console.log(`Architecture checks passed (${files.length} modules).`);
