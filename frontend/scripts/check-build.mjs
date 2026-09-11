import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "@babel/parser";

const root = fileURLToPath(new URL("../../src/aespa/web/", import.meta.url));
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
for (const file of ["app.js", "styles.css"]) {
  if (!html.includes(`/${file}?v=__AESPA_ASSET_VERSION__`))
    throw new Error(`Missing versioned ${file} in HTML`);
}
for (const file of ["app.js", "styles.css", "sw.js", "manifest.json", "icon.png", "icon-sm.png"]) {
  if (!fs.existsSync(path.join(root, file))) throw new Error(`Missing packaged asset: ${file}`);
}
const walk = (dir) =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(file) : [file];
  });
const files = walk(root);
const css = files.filter((file) => file.endsWith(".css"));
if (css.length !== 1 || path.basename(css[0]) !== "styles.css")
  throw new Error("FastAPI expects one versioned stylesheet");
function checkImports(node, file) {
  if (!node || typeof node !== "object") return;
  const source =
    node.type === "ImportDeclaration" ||
    node.type === "ExportNamedDeclaration" ||
    node.type === "ExportAllDeclaration"
      ? node.source?.value
      : node.type === "ImportExpression"
        ? node.source?.value
        : undefined;
  if (source?.startsWith(".") && !fs.existsSync(path.resolve(path.dirname(file), source))) {
    throw new Error(`${path.basename(file)} refers to missing chunk ${source}`);
  }
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) value.forEach((item) => checkImports(item, file));
    else if (value && typeof value === "object") checkImports(value, file);
  }
}
for (const file of files.filter((file) => file.endsWith(".js"))) {
  checkImports(
    parse(fs.readFileSync(file, "utf8"), {
      sourceType: "unambiguous",
      createImportExpressions: true,
    }),
    file,
  );
}
console.log("Built assets match the FastAPI and desktop packaging contract.");
