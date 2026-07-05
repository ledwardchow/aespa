export const OWASP_WEB_LABELS = {
  A01: "Broken Access Control",
  A02: "Cryptographic Failures",
  A03: "Injection",
  A04: "Insecure Design",
  A05: "Security Misconfiguration",
  A06: "Software & Data Supply Chain Failures",
  A07: "Identification & Auth Failures",
  A08: "Software & Data Integrity Failures",
  A09: "Logging & Monitoring Failures",
  A10: "SSRF"
};

export const ALICE_DEDUP_DIRECTIVE =
  "Review all of the findings recorded for this scan and remove duplicates. " +
  "Use the finding_list context tool to load every finding, then identify the ones that " +
  "describe the same vulnerability on the same endpoint or target, and remove the duplicates. " +
  "If multiple findings describe the same underlying issue but with somewhat different details, " +
  "you can consolidate them into a single finding by re-writing it (write a new issue then delete the " +
  "superseded ones). Do not run any new HTTP requests, browser actions, or probes — this is a " +
  "findings cleanup task only. When you finish, briefly summarize the changes made.";
