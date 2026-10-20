import { expect, test } from "vitest";

import { callbackExample, curlExamples, responseExample, sampleValue } from "./apiExamples.js";

const document = {
  components: {
    schemas: {
      ScanStatus: {
        type: "object",
        examples: [{ id: "web-42", state: "running" }],
        properties: { id: { type: "string" } },
      },
      SourceScanCreate: {
        type: "object",
        required: ["provider_id"],
        properties: {
          provider_id: { type: "string" },
          start: { type: "boolean", default: true },
        },
      },
      Body_upload: {
        type: "object",
        required: ["file"],
        properties: {
          file: { type: "string", contentMediaType: "application/octet-stream" },
          name: { anyOf: [{ type: "string" }, { type: "null" }] },
          start: { type: "boolean", default: true },
        },
      },
      CallbackPayload: {
        type: "object",
        properties: {
          id: { type: "string" },
          event: { enum: ["scan.started", "scan.completed"] },
          scan: { $ref: "#/components/schemas/ScanStatus" },
        },
      },
    },
  },
};

const secured = { security: [{ bearerAuth: [] }] };

test("uses published request examples and fills in path values", () => {
  const calls = curlExamples(document, {
    baseUrl: "http://127.0.0.1:8000/extension/aespa.api",
    path: "/v1/scans/{scan_id}/start",
    method: "post",
    operation: {
      ...secured,
      parameters: [
        { name: "scan_id", in: "path", required: true, schema: { pattern: "^(web|sast)-[0-9]+$" } },
      ],
      requestBody: {
        content: {
          "application/json": {
            schema: { $ref: "#/components/schemas/SourceScanCreate" },
            examples: {
              one: { summary: "First", value: { provider_id: "a" } },
              two: { summary: "Second", value: { provider_id: "it's" } },
            },
          },
        },
      },
    },
  });
  expect(calls.map((call) => call.summary)).toEqual(["First", "Second"]);
  expect(calls[0].command).toContain(
    "curl -X POST 'http://127.0.0.1:8000/extension/aespa.api/v1/scans/web-42/start'",
  );
  expect(calls[0].command).toContain('-H "Authorization: Bearer $AESPA_TOKEN"');
  expect(calls[0].command).toContain("-H 'Content-Type: application/json'");
  expect(calls[1].command).toContain(`"provider_id": "it'\\''s"`);
});

test("builds required-only bodies and multipart forms without published examples", () => {
  const [json] = curlExamples(document, {
    baseUrl: "",
    path: "/v1/sast/scans/from-source",
    method: "post",
    operation: {
      requestBody: {
        content: {
          "application/json": { schema: { $ref: "#/components/schemas/SourceScanCreate" } },
        },
      },
    },
  });
  expect(json.command).toContain('"provider_id": "provider-id"');
  expect(json.command).not.toContain("start");
  expect(json.command).not.toContain("Authorization");

  const [form] = curlExamples(document, {
    baseUrl: "",
    path: "/v1/sast/scans",
    method: "post",
    operation: {
      requestBody: {
        content: {
          "multipart/form-data": { schema: { $ref: "#/components/schemas/Body_upload" } },
        },
      },
    },
  });
  expect(form.command).toContain("-F 'file=@source.zip'");
  expect(form.command).toContain("-F 'name=Example name'");
  expect(form.command).not.toContain("start=");
});

test("uses schema examples for responses and callbacks", () => {
  expect(
    responseExample(document, {
      responses: {
        200: {
          content: {
            "application/json": { schema: { $ref: "#/components/schemas/ScanStatus" } },
          },
        },
      },
    }),
  ).toEqual({ id: "web-42", state: "running" });
  expect(
    responseExample(document, {
      responses: {
        201: {
          content: {
            "application/json": {
              schema: { $ref: "#/components/schemas/ScanStatus" },
              example: { id: "sast-17" },
            },
          },
        },
      },
    }),
  ).toEqual({ id: "sast-17" });
  expect(sampleValue(document, { type: "array", items: { type: "integer", minimum: 5 } })).toEqual([
    5,
  ]);
  const callback = callbackExample(document, "scan.completed", {
    requestBody: {
      content: {
        "application/json": { schema: { $ref: "#/components/schemas/CallbackPayload" } },
      },
    },
  });
  expect(callback).toContain("X-AESPA-Event: scan.completed");
  expect(callback).toContain('"event": "scan.completed"');
  expect(callback).toContain('"state": "completed"');
});
