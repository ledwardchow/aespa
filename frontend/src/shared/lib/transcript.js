export function apiTranscriptText(text) {
  if (!text) return "";
  const value = String(text).trim();
  return value.includes("REQUEST\n") && value.includes("RESPONSE\n") ? value : "";
}
