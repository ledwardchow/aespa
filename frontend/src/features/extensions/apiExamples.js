// Build example calls and payloads from an OpenAPI document. Published
// examples are used when the definition has them; otherwise values are made
// up from each field's type.

const MAX_DEPTH = 6;

function refName(ref) {
  return ref ? ref.split("/").pop() : "";
}

function resolve(document, schema) {
  let current = schema || {};
  for (let depth = 0; current.$ref && depth < 10; depth += 1) {
    current = document.components?.schemas?.[refName(current.$ref)] || {};
  }
  return current;
}

function stringSample(name, schema) {
  if (schema.format === "binary" || schema.contentMediaType) return "@source.zip";
  if (name === "name") return "Example name";
  if (schema.format === "uri" || /url$/i.test(name)) return "https://example.com";
  if (schema.format === "date-time" || /_at$/.test(name)) return "2026-10-16T09:00:00+00:00";
  if (schema.format === "password") return "change-me";
  if (schema.pattern?.includes("web|sast")) return "web-42";
  return name ? name.replace(/_/g, "-") : "string";
}

// Schema tools sort example keys alphabetically. Put them back in the order the
// object's fields are defined so examples read like real responses.
function orderLike(document, schema, value, depth = 0) {
  if (depth > MAX_DEPTH || value === null || typeof value !== "object") return value;
  let resolved = resolve(document, schema);
  if (resolved.anyOf || resolved.oneOf) {
    resolved = resolve(
      document,
      (resolved.anyOf || resolved.oneOf).find((item) => item.type !== "null"),
    );
  }
  if (Array.isArray(value)) {
    return value.map((item) => orderLike(document, resolved.items, item, depth + 1));
  }
  const properties = resolved.properties || {};
  const keys = [
    ...Object.keys(properties).filter((key) => key in value),
    ...Object.keys(value).filter((key) => !(key in properties)),
  ];
  return Object.fromEntries(
    keys.map((key) => [key, orderLike(document, properties[key], value[key], depth + 1)]),
  );
}

export function sampleValue(document, schema, { name = "", requiredOnly = false, depth = 0 } = {}) {
  if (!schema || depth > MAX_DEPTH) return null;
  if (schema.example !== undefined) return schema.example;
  if (Array.isArray(schema.examples) && schema.examples.length) {
    return orderLike(document, schema, schema.examples[0]);
  }
  if (schema.default !== undefined && schema.default !== null) return schema.default;
  if (schema.const !== undefined) return schema.const;
  if (schema.enum?.length) return schema.enum[0];
  if (schema.$ref) {
    return sampleValue(document, resolve(document, schema), {
      name,
      requiredOnly,
      depth: depth + 1,
    });
  }
  if (schema.anyOf || schema.oneOf) {
    const option = (schema.anyOf || schema.oneOf).find((item) => item.type !== "null");
    return option ? sampleValue(document, option, { name, requiredOnly, depth: depth + 1 }) : null;
  }
  const type =
    schema.type ||
    (schema.pattern || schema.format || schema.contentMediaType ? "string" : undefined);
  switch (type) {
    case "string":
      return stringSample(name, schema);
    case "integer":
      return Math.max(1, schema.minimum ?? 1);
    case "number":
      return 1.5;
    case "boolean":
      return true;
    case "array": {
      const item = sampleValue(document, schema.items, { name, requiredOnly, depth: depth + 1 });
      return item === null ? [] : [item];
    }
    default: {
      const properties = Object.entries(schema.properties || {});
      if (!properties.length) return {};
      const required = new Set(schema.required || []);
      const result = {};
      for (const [key, property] of properties) {
        if (requiredOnly && !required.has(key)) continue;
        result[key] = sampleValue(document, property, {
          name: key,
          requiredOnly,
          depth: depth + 1,
        });
      }
      return result;
    }
  }
}

function quote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`;
}

function pathWithValues(document, path, parameters) {
  return path.replace(/\{([^}]+)\}/g, (_, key) => {
    const parameter = parameters.find((item) => item.in === "path" && item.name === key);
    return String(sampleValue(document, parameter?.schema || {}, { name: key }) ?? key);
  });
}

function formLines(document, schema) {
  const resolved = resolve(document, schema);
  const required = new Set(resolved.required || []);
  return Object.entries(resolved.properties || {})
    .filter(([key]) => required.has(key) || key === "name")
    .map(([key, property]) => {
      const value = sampleValue(document, property, { name: key });
      return `-F ${quote(`${key}=${value}`)}`;
    });
}

/** Example curl commands for one operation, one per published request example. */
export function curlExamples(document, { baseUrl, path, method, operation }) {
  const parameters = operation.parameters || [];
  const query = parameters
    .filter((item) => item.in === "query" && item.required)
    .map(
      (item) =>
        `${item.name}=${encodeURIComponent(sampleValue(document, item.schema, { name: item.name }))}`,
    );
  const url = `${baseUrl}${pathWithValues(document, path, parameters)}${query.length ? `?${query.join("&")}` : ""}`;
  const head = [`curl -X ${method.toUpperCase()} ${quote(url)}`];
  if (operation.security?.length) head.push(`-H "Authorization: Bearer $AESPA_TOKEN"`);

  const content = operation.requestBody?.content || {};
  const type = Object.keys(content)[0];
  const lines = (extra) => [...head, ...extra].join(" \\\n  ");
  if (!type) return [{ name: "default", summary: "", command: lines([]) }];
  if (type === "multipart/form-data") {
    return [
      { name: "default", summary: "", command: lines(formLines(document, content[type].schema)) },
    ];
  }
  const published = Object.entries(content[type].examples || {});
  const bodies = published.length
    ? published.map(([name, example]) => ({
        name,
        summary: example.summary || name,
        value: example.value,
      }))
    : [
        {
          name: "default",
          summary: "",
          value: sampleValue(document, content[type].schema, { requiredOnly: true }),
        },
      ];
  return bodies.map((body) => ({
    name: body.name,
    summary: body.summary,
    command: lines([
      `-H 'Content-Type: ${type}'`,
      `-d ${quote(JSON.stringify(body.value, null, 2))}`,
    ]),
  }));
}

/** An example of the operation's first successful JSON response, if it has one. */
export function responseExample(document, operation) {
  const success = Object.entries(operation.responses || {}).find(([code]) => /^2/.test(code));
  const content = success?.[1]?.content?.["application/json"];
  if (!content?.schema) return null;
  const published = content.example ?? Object.values(content.examples || {})[0]?.value;
  if (published !== undefined) return orderLike(document, content.schema, published);
  return sampleValue(document, content.schema);
}

const EVENT_STATES = {
  "scan.started": "running",
  "scan.phase_changed": "running",
  "scan.progress": "running",
  "scan.needs_action": "needs_action",
  "scan.paused": "paused",
  "scan.completed": "completed",
  "scan.failed": "failed",
  "scan.stopped": "stopped",
};
const FINAL_STATES = new Set(["completed"]);

/** The JSON body of a callback event. */
export function callbackExample(document, event, operation) {
  const schema = operation.requestBody?.content?.["application/json"]?.schema;
  if (!schema) return null;
  const body = sampleValue(document, schema);
  if (body && typeof body === "object") {
    body.event = event;
    const state = EVENT_STATES[event];
    if (state && body.scan && typeof body.scan === "object") {
      body.scan = { ...body.scan, state, ...(FINAL_STATES.has(state) ? { percent: 100 } : {}) };
      if (state === "failed") body.scan.error = "The browser closed unexpectedly.";
    }
    body.id = "6f1c2a4e-1b7d-4a55-9c1e-2f3a4b5c6d7e";
  }
  const json = JSON.stringify(body, null, 2);
  return [
    `POST <your callback URL>`,
    "Content-Type: application/json",
    `X-AESPA-Event: ${event}`,
    "X-AESPA-Delivery: 6f1c2a4e-1b7d-4a55-9c1e-2f3a4b5c6d7e",
    "X-AESPA-Signature: t=1792141200,v1=5d41402abc4b2a76b9719d911017c592...",
    "",
    json,
  ].join("\n");
}
