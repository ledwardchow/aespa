export const normalizeAliceText = (text) => {
  if (!text || typeof text !== "string") return text || "";
  return text
    .replace(/<\/?think(?:ing)?>/gi, "")
    .replace(/\[\[ALICE_SAY\]\]\s*<\/?think(?:ing)?>/gi, "[[ALICE_SAY]]")
    .replace(/<\/?think(?:ing)?>\s*\[\[\/ALICE_SAY\]\]/gi, "[[/ALICE_SAY]]")
    .replace(/\n{3,}/g, "\n\n");
};
