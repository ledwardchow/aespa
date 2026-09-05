export function markdownText(value) {
  if (value == null) return "";
  if (typeof value === "string") return value.trim();
  if (typeof value === "object") {
    // Flatten content-block shapes ({text}/[{text}]) the LLM sometimes returns
    // so they never render as the literal "[object Object]".
    if (Array.isArray(value)) return value.map(markdownText).filter(Boolean).join("\n").trim();
    if (typeof value.text === "string") return value.text.trim();
    try {
      return JSON.stringify(value);
    } catch {
      return "";
    }
  }
  return String(value).trim();
}

export function markdownListValue(value) {
  const text = markdownText(value);
  return text || "—";
}

export function markdownCodeBlock(value) {
  const text = markdownText(value);
  if (!text) return "—";
  const fence = text.includes("```") ? "````" : "```";
  return `${fence}\n${text}\n${fence}`;
}

export function slugForFilename(value) {
  return (
    String(value || "issues")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80) || "issues"
  );
}
