const FIELD_RE = /^-\s+\*\*([^*]+):\*\*\s*(.*)$/;
const CATEGORY_RE = /^##\s+(A\d{2}\s*:\s*.+)$/i;
const ITEM_RE = /^###\s+(\d+)\.\s+(.+)$/;
const CODE_RE = /`([^`]+)`/g;
const SOURCE_PATH_RE = /(?:^|\/)[^\s`]+\.(?:php|py|js|jsx|ts|tsx|java|go|rb|rs|cs|cpp|c|h|html|vue|svelte)$/i;
const HTTP_OPERATION_RE = /\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(\/[^\s`"'}]+)/i;

function cleanMarkdown(value = "") {
  return value
    .replace(/\[([^\]]+)]\([^)]+\)/g, "$1")
    .replace(/\*/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function codeValues(value = "") {
  return [...value.matchAll(CODE_RE)].map((match) => match[1].trim());
}

function locationsFrom(value = "") {
  const seen = new Set();
  return codeValues(value)
    .filter((candidate) => SOURCE_PATH_RE.test(candidate))
    .filter((path) => {
      if (seen.has(path)) return false;
      seen.add(path);
      return true;
    })
    .map((path) => ({ path }));
}

function operationFrom(fields) {
  const text = [fields.exploit, fields.discovery, fields.description].filter(Boolean).join(" ");
  const match = text.match(HTTP_OPERATION_RE);
  return match ? `${match[1].toUpperCase()} ${match[2]}` : "";
}

function finishItem(item, category) {
  if (!item) return null;
  const fields = Object.fromEntries(
    Object.entries(item.fields).map(([key, value]) => [key, cleanMarkdown(value)]),
  );
  const expectedEvidence = [fields.exploit, fields.discovery, fields["ui entry point"]].filter(
    Boolean,
  );
  return {
    external_id: `GT-${item.number}`,
    title: cleanMarkdown(item.title),
    description: fields.description || "",
    category: category || "",
    severity: "medium",
    locations: locationsFrom(item.fields.file),
    root_cause: fields.description || "",
    affected_operation: operationFrom(fields),
    expected_evidence: expectedEvidence,
    classification: "exploitable",
  };
}

export function parseMarkdownGroundTruth(text, filename = "ground-truth.md") {
  const lines = text.replace(/\r\n?/g, "\n").split("\n");
  const title = lines.find((line) => /^#\s+/.test(line))?.replace(/^#\s+/, "").trim();
  const items = [];
  let category = "";
  let item = null;
  let activeField = null;

  const flush = () => {
    const parsed = finishItem(item, category);
    if (parsed) items.push(parsed);
    item = null;
    activeField = null;
  };

  for (const line of lines) {
    const categoryMatch = line.match(CATEGORY_RE);
    if (categoryMatch) {
      flush();
      category = cleanMarkdown(categoryMatch[1]);
      continue;
    }
    if (/^##\s+/.test(line)) {
      flush();
      category = "";
      continue;
    }
    const itemMatch = line.match(ITEM_RE);
    if (itemMatch) {
      flush();
      item = { number: itemMatch[1], title: itemMatch[2], fields: {} };
      continue;
    }
    if (!item) continue;
    const fieldMatch = line.match(FIELD_RE);
    if (fieldMatch) {
      activeField = fieldMatch[1].trim().toLowerCase();
      item.fields[activeField] = fieldMatch[2].trim();
      continue;
    }
    if (activeField && line.trim() && !/^---+$/.test(line.trim())) {
      item.fields[activeField] = `${item.fields[activeField]} ${line.trim()}`.trim();
    }
  }
  flush();

  if (!items.length) {
    throw new Error(
      "No vulnerability entries were found. Markdown entries must use headings such as '### 1. Title'.",
    );
  }
  const ids = new Set(items.map((entry) => entry.external_id));
  if (ids.size !== items.length) throw new Error("Vulnerability numbers must be unique.");
  return {
    schema_version: 1,
    name: title || filename.replace(/\.(?:md|markdown)$/i, ""),
    items,
  };
}

export function parseGroundTruthText(text, filename = "ground-truth.json") {
  const trimmed = text.trimStart();
  if (
    /\.md(?:own)?$/i.test(filename) ||
    (!trimmed.startsWith("[") && !trimmed.startsWith("{"))
  ) {
    return parseMarkdownGroundTruth(text, filename);
  }
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("Ground truth must be valid JSON or supported Markdown.");
  }
  if (Array.isArray(parsed)) parsed = { schema_version: 1, items: parsed };
  if (!parsed || !Array.isArray(parsed.items)) {
    throw new Error("Ground-truth JSON must contain an items array.");
  }
  return parsed;
}
