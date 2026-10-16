import { expect, test } from "vitest";

import { fmtDate, fmtTime, parseDate } from "./dates.js";

test("reads server times without a time zone as UTC", () => {
  expect(parseDate("2026-10-16T04:05:06").toISOString()).toBe("2026-10-16T04:05:06.000Z");
  expect(parseDate("2026-10-16 04:05:06.123").toISOString()).toBe("2026-10-16T04:05:06.123Z");
});

test("keeps an explicit time zone", () => {
  expect(parseDate("2026-10-16T04:05:06+11:00").toISOString()).toBe("2026-10-15T17:05:06.000Z");
});

test("formats missing and invalid values with a fallback", () => {
  expect(fmtTime(null)).toBe("—");
  expect(fmtTime("", "--:--:--")).toBe("--:--:--");
  expect(fmtTime("not a date", "")).toBe("");
  expect(fmtDate(null)).toBe("—");
  expect(fmtDate("not a date")).toBe("not a date");
});

test("formats times as 24-hour HH:MM:SS", () => {
  expect(fmtTime("2026-10-16T04:05:06")).toMatch(/^\d{2}:\d{2}:\d{2}$/);
});
