import { normalizeAliceText } from "./text.js";

export const pushVisibleAndThinkSegments = (segments, text, visibleKind) => {
  if (!text) return;
  const thinkRe = /<think(?:ing)?\b[^>]*>([\s\S]*?)<\/think(?:ing)?>/gi;
  let lastIndex = 0;
  let m;
  while ((m = thinkRe.exec(text)) !== null) {
    const before = normalizeAliceText(text.slice(lastIndex, m.index)).trim();
    if (before)
      segments.push({
        kind: visibleKind,
        text: before,
      });
    const thought = normalizeAliceText(m[1] || "").trim();
    if (thought)
      segments.push({
        kind: "trace",
        text: thought,
      });
    lastIndex = m.index + m[0].length;
  }

  let tail = text.slice(lastIndex);
  const openThink = tail.match(/<think(?:ing)?\b[^>]*>/i);
  if (openThink && openThink.index !== undefined) {
    const before = normalizeAliceText(tail.slice(0, openThink.index)).trim();
    if (before)
      segments.push({
        kind: visibleKind,
        text: before,
      });
    const thought = normalizeAliceText(tail.slice(openThink.index + openThink[0].length)).trim();
    if (thought)
      segments.push({
        kind: "trace",
        text: thought,
      });
    return;
  }

  tail = normalizeAliceText(tail).trim();
  if (tail)
    segments.push({
      kind: visibleKind,
      text: tail,
    });
};

export const ALICE_SAY_RE = /\[\[ALICE_SAY\]\]([\s\S]*?)\[\[\/ALICE_SAY\]\]/g;

export const parseAliceTurnSegments = (text) => {
  if (!text) return [];
  const segments = [];
  let lastIndex = 0;
  let m;
  ALICE_SAY_RE.lastIndex = 0;
  while ((m = ALICE_SAY_RE.exec(text)) !== null) {
    const before = text.slice(lastIndex, m.index);
    pushVisibleAndThinkSegments(segments, before, "trace");
    pushVisibleAndThinkSegments(segments, m[1], "message");
    lastIndex = m.index + m[0].length;
  }
  const tail = text.slice(lastIndex);
  pushVisibleAndThinkSegments(segments, tail, "trace");
  return segments;
};
