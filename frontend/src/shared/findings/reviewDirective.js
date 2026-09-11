export const ALICE_DEDUP_DIRECTIVE =
  "Review all of the findings recorded for this scan and remove duplicates. " +
  "Use the finding_list context tool to load every finding, then identify the ones that " +
  "describe the same vulnerability on the same endpoint or target, and remove the duplicates. " +
  "If multiple findings describe the same underlying issue but with somewhat different details, " +
  "you can consolidate them into a single finding by re-writing it (write a new issue then delete the " +
  "superseded ones). Do not run any new HTTP requests, browser actions, or probes — this is a " +
  "findings cleanup task only. When you finish, briefly summarize the changes made.";
