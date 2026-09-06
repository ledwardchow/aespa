import { expect, test } from "vitest";

import { campaignDisplayWarnings } from "./campaignPresentation.js";

test("hides resolved restart guidance after a campaign resumes", () => {
  const warning = "The application restarted while this stage was running. Retry to resume.";
  expect(
    campaignDisplayWarnings({ status: "interrupted", warnings_json: JSON.stringify([warning]) }),
  ).toEqual([warning]);
  expect(
    campaignDisplayWarnings({ status: "correlating", warnings_json: JSON.stringify([warning]) }),
  ).toEqual([]);
});
