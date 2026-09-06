import { describe, expect, it } from "vitest";

import {
  blockersFor,
  caseSourceLead,
  orderedHops,
  validationCasesFromResponse,
} from "./ValidationCases.jsx";

describe("validation case presentation", () => {
  it("keeps browser and service hops in the source order", () => {
    const hops = orderedHops({
      frontend_surface: {
        ui_route: { kind: "ui_route", path: "/quotes/motor" },
        ui_action: { kind: "ui_action", action: "Submit quote" },
        browser_request: {
          request_role: "browser_request",
          method: "POST",
          path: "/api/quotes/motor",
        },
      },
      service_hops: [
        { request_role: "server_egress", method: "POST", path: "/api/customer/quotes/motor" },
        { kind: "route", path: "/api/customer/quotes/motor" },
      ],
      vulnerability_anchor: { kind: "lead_anchor", location: "policy.py:42" },
    });

    expect(hops.map((hop) => hop.request_role || hop.kind)).toEqual([
      "ui_route",
      "ui_action",
      "browser_request",
      "server_egress",
      "route",
      "lead_anchor",
    ]);
    expect(hops[2].path).toBe("/api/quotes/motor");
    expect(hops[3].path).toBe("/api/customer/quotes/motor");
  });

  it("reads legacy mappings without treating them as live", () => {
    const hops = orderedHops(null, {
      frontend_entrypoint: { method: "POST", path: "/legacy" },
      backend_route: { method: "POST", path: "/internal/legacy" },
    });
    expect(hops.map((hop) => hop.kind)).toEqual(["http_call", "route"]);
  });

  it("accepts both response envelopes and preserves source lead context", () => {
    const validationCase = {
      origin_lead_id: 9,
      source_lead: { reference: "OQDD-005", title: "Missing validation" },
      blocker_codes: '["missing_interaction"]',
    };
    expect(validationCasesFromResponse({ cases: [validationCase] })).toEqual([validationCase]);
    expect(caseSourceLead(validationCase)).toMatchObject({
      id: 9,
      reference: "OQDD-005",
      title: "Missing validation",
    });
    expect(blockersFor(validationCase)).toEqual(["missing_interaction"]);
  });
});
