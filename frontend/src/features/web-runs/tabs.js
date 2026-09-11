export const WEB_RUN_TABS = [
  { key: "activity", label: "Status" },
  { key: "sitemap", label: "Site Map" },
  { key: "attack", label: "Attack Surface & Coverage" },
  { key: "sessions", label: "Sessions" },
  { key: "findings", label: "Findings" },
  { key: "traffic", label: "Traffic Log" },
  { key: "leads", label: "SAST Leads" },
];

export function normaliseWebTab(tab) {
  if (["tasks", "workprogram", "intelligence"].includes(tab)) return "attack";
  return WEB_RUN_TABS.some((item) => item.key === tab) ? tab : "activity";
}
