import { useEffect, useMemo, useState } from "react";

import { getApiDefinition } from "../../shared/api/integrationApi.js";
import { callbackExample, curlExamples, responseExample } from "./apiExamples.js";
import { permissionLabels } from "./apiPermissions.js";

const METHODS = ["get", "post", "put", "patch", "delete"];

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

export function typeLabel(schema) {
  if (!schema) return "";
  if (schema.$ref) return refName(schema.$ref);
  if (schema.anyOf || schema.oneOf) {
    return (schema.anyOf || schema.oneOf)
      .filter((item) => item.type !== "null")
      .map(typeLabel)
      .join(" or ");
  }
  if (schema.enum) return schema.enum.map((value) => JSON.stringify(value)).join(" | ");
  if (schema.const !== undefined) return JSON.stringify(schema.const);
  if (schema.type === "array") return `${typeLabel(schema.items) || "value"}[]`;
  if (schema.format === "binary") return "file";
  return schema.type || "object";
}

function download(name, document) {
  const blob = new Blob([JSON.stringify(document, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = window.document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

function objectId(name) {
  return `api-object-${name}`;
}

// Open a Data objects entry and scroll to it. The app uses hash routes, so
// these links cannot be plain #anchors.
function showObject(name) {
  const entry = window.document.getElementById(objectId(name));
  if (!entry) return;
  entry.open = true;
  entry.scrollIntoView({ block: "start" });
}

// The object a field holds, looking through arrays, optional values, and refs.
function nestedObject(document, schema) {
  let current = schema || {};
  for (let depth = 0; depth < 10; depth += 1) {
    if (current.anyOf || current.oneOf) {
      const options = (current.anyOf || current.oneOf).filter((item) => item.type !== "null");
      if (options.length !== 1) return null;
      current = options[0];
    } else if (current.type === "array" && current.items) {
      current = current.items;
    } else {
      break;
    }
  }
  if (!current.$ref) return null;
  const name = refName(current.$ref);
  const resolved = resolve(document, current);
  return resolved.properties ? { name, schema: resolved } : null;
}

function TypeLabel({ document, schema }) {
  if (!schema) return null;
  if (schema.$ref) {
    const name = refName(schema.$ref);
    return document.components?.schemas?.[name] ? (
      <button type="button" className="api-def-link" onClick={() => showObject(name)}>
        {name}
      </button>
    ) : (
      name
    );
  }
  if (schema.anyOf || schema.oneOf) {
    const options = (schema.anyOf || schema.oneOf).filter((item) => item.type !== "null");
    return options.map((item, index) => (
      <span key={index}>
        {index ? " or " : null}
        <TypeLabel document={document} schema={item} />
      </span>
    ));
  }
  if (schema.type === "array") {
    return (
      <>{schema.items ? <TypeLabel document={document} schema={schema.items} /> : "value"}[]</>
    );
  }
  return typeLabel(schema);
}

function FieldRow({ document, name, schema, required, note, seen }) {
  const [open, setOpen] = useState(false);
  const nested = nestedObject(document, schema);
  const repeated = nested && seen.includes(nested.name);
  return (
    <>
      <tr>
        <td className="api-def-name">
          {name}
          {required ? <span className="api-def-required"> required</span> : null}
        </td>
        <td className="api-def-type">
          <TypeLabel document={document} schema={schema} />
          {schema?.writeOnly ? <span className="api-def-required"> never returned</span> : null}
          {nested && !repeated ? (
            <button
              type="button"
              className="api-def-toggle"
              aria-expanded={open}
              onClick={() => setOpen((value) => !value)}
            >
              {open ? "Hide fields" : "Show fields"}
            </button>
          ) : null}
        </td>
        <td className="subtle">{note || ""}</td>
      </tr>
      {open && nested && !repeated ? (
        <tr className="api-def-nested">
          <td colSpan={3}>
            <SchemaFields
              document={document}
              schema={nested.schema}
              seen={[...seen, nested.name]}
            />
          </td>
        </tr>
      ) : null}
    </>
  );
}

function SchemaFields({ document, schema, seen = [] }) {
  const resolved = resolve(document, schema);
  const properties = Object.entries(resolved.properties || {});
  if (!properties.length) {
    return (
      <div className="subtle api-def-note">
        {schema ? <TypeLabel document={document} schema={schema} /> : "No body"}
      </div>
    );
  }
  const required = new Set(resolved.required || []);
  const own = schema?.$ref ? [...seen, refName(schema.$ref)] : seen;
  return (
    <table className="api-def-table">
      <tbody>
        {properties.map(([name, property]) => (
          <FieldRow
            key={name}
            document={document}
            name={name}
            schema={property}
            required={required.has(name)}
            note={property.description}
            seen={own}
          />
        ))}
      </tbody>
    </table>
  );
}

function DataObjects({ document }) {
  const schemas = Object.entries(document.components?.schemas || {}).sort(([a], [b]) =>
    a.localeCompare(b),
  );
  if (!schemas.length) return null;
  return (
    <div className="api-def-group">
      <div className="extension-subsection-title">Data objects</div>
      <div className="subtle api-def-note" style={{ marginBottom: 8 }}>
        The objects that requests and responses use. Select an object name anywhere above to open it
        here.
      </div>
      {schemas.map(([name, schema]) => (
        <details key={name} id={objectId(name)} className="api-def-operation">
          <summary>
            <code className="api-def-path">{name}</code>
            <span className="api-def-summary">{firstSentence(schema.description || "")}</span>
          </summary>
          <div className="api-def-details">
            {schema.description ? (
              <p className="subtle api-def-description">{schema.description}</p>
            ) : null}
            <SchemaFields document={document} schema={{ $ref: `#/components/schemas/${name}` }} />
          </div>
        </details>
      ))}
    </div>
  );
}

function CodeBlock({ label, text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="api-def-code-wrap">
      <pre className="api-def-code" aria-label={label}>
        {text}
      </pre>
      <button className="btn secondary sm api-def-copy" type="button" onClick={copy}>
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

function Examples({ document, baseUrl, path, method, operation, isEvent }) {
  const calls = useMemo(
    () => (isEvent ? [] : curlExamples(document, { baseUrl, path, method, operation })),
    [document, baseUrl, path, method, operation, isEvent],
  );
  const [selected, setSelected] = useState(0);
  if (isEvent) {
    return (
      <>
        <div className="api-def-heading">Example request from AESPA</div>
        <CodeBlock
          label={`Example ${path} callback`}
          text={callbackExample(document, path, operation)}
        />
      </>
    );
  }
  const call = calls[Math.min(selected, calls.length - 1)];
  const response = responseExample(document, operation);
  return (
    <>
      <div className="api-def-heading">Example call</div>
      {calls.length > 1 ? (
        <div className="row api-def-example-choices" role="group" aria-label="Examples">
          {calls.map((item, index) => (
            <button
              key={item.name}
              type="button"
              className={`btn sm ${index === selected ? "" : "secondary"}`}
              aria-pressed={index === selected}
              onClick={() => setSelected(index)}
            >
              {item.summary}
            </button>
          ))}
        </div>
      ) : null}
      <CodeBlock label={`Example ${method.toUpperCase()} ${path}`} text={call.command} />
      {response !== null ? (
        <>
          <div className="api-def-heading">Example response</div>
          <CodeBlock
            label={`Example response for ${method.toUpperCase()} ${path}`}
            text={JSON.stringify(response, null, 2)}
          />
        </>
      ) : null}
    </>
  );
}

function OperationDetails({ document, operation, baseUrl, path, method, isEvent }) {
  const parameters = operation.parameters || [];
  const body = operation.requestBody?.content;
  const bodyType = body ? Object.keys(body)[0] : null;
  const responses = Object.entries(operation.responses || {});
  return (
    <div className="api-def-details">
      {operation.description ? <p className="subtle">{operation.description}</p> : null}
      {parameters.length ? (
        <>
          <div className="api-def-heading">Parameters</div>
          <table className="api-def-table">
            <tbody>
              {parameters.map((parameter) => (
                <tr key={`${parameter.in}-${parameter.name}`}>
                  <td className="api-def-name">
                    {parameter.name}
                    {parameter.required ? (
                      <span className="api-def-required"> required</span>
                    ) : null}
                  </td>
                  <td className="api-def-type">
                    {parameter.in} · <TypeLabel document={document} schema={parameter.schema} />
                  </td>
                  <td className="subtle">{parameter.description || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}
      {bodyType ? (
        <>
          <div className="api-def-heading">Request body ({bodyType})</div>
          <SchemaFields document={document} schema={body[bodyType].schema} />
        </>
      ) : null}
      <div className="api-def-heading">Responses</div>
      <table className="api-def-table">
        <tbody>
          {responses.map(([code, response]) => {
            const content = response.content || {};
            const type = Object.keys(content)[0];
            return (
              <FieldRow
                key={code}
                document={document}
                name={code}
                schema={type ? content[type].schema : null}
                note={response.description}
                seen={[]}
              />
            );
          })}
        </tbody>
      </table>
      <Examples
        document={document}
        baseUrl={baseUrl}
        path={path}
        method={method}
        operation={operation}
        isEvent={isEvent}
      />
    </div>
  );
}

function firstSentence(text = "") {
  const match = text.match(/^.*?[.!?](\s|$)/);
  return (match ? match[0] : text).trim();
}

function Operation({ document, baseUrl, method, path, operation, isEvent = false }) {
  const scopes = operation["x-aespa-scopes"] || [];
  return (
    <details className="api-def-operation">
      <summary>
        <span className={`api-def-method ${isEvent ? "event" : method}`}>
          {isEvent ? "EVENT" : method.toUpperCase()}
        </span>
        <code className="api-def-path">{path}</code>
        <span className="api-def-summary">
          {isEvent ? firstSentence(operation.description) : operation.summary}
        </span>
        {scopes.length ? (
          <span className="subtle api-def-scopes">Permission: {permissionLabels(scopes)}</span>
        ) : null}
      </summary>
      <OperationDetails
        document={document}
        operation={operation}
        baseUrl={baseUrl}
        path={path}
        method={method}
        isEvent={isEvent}
      />
    </details>
  );
}

export function ApiDefinition({ extension }) {
  const [document, setDocument] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    getApiDefinition(extension.openapi_url)
      .then((loaded) => active && setDocument(loaded))
      .catch((loadError) => active && setError(loadError.message));
    return () => {
      active = false;
    };
  }, [extension.openapi_url]);

  const groups = useMemo(() => {
    if (!document) return [];
    const byTag = new Map();
    for (const [path, operations] of Object.entries(document.paths || {})) {
      for (const method of METHODS) {
        const operation = operations[method];
        if (!operation) continue;
        const tag = operation.tags?.[0] || "Other";
        if (!byTag.has(tag)) byTag.set(tag, []);
        byTag.get(tag).push({ path, method, operation });
      }
    }
    return [...byTag.entries()];
  }, [document]);

  const baseUrl = document ? `${window.location.origin}${document.servers?.[0]?.url || ""}` : "";
  const callbacks = Object.entries(document?.webhooks || {});

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(baseUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section className="card api-def" aria-label="API definition">
      <div className="form-section-title">API definition</div>
      {error ? <div className="alert error">{error}</div> : null}
      {!document && !error ? <div className="subtle">Loading…</div> : null}
      {document ? (
        <>
          <div className="subtle" style={{ marginTop: 4 }}>
            {document.info?.title} {document.info?.version} · OpenAPI {document.openapi}
          </div>
          <div className="field" style={{ marginTop: 12 }}>
            <label htmlFor="api-def-base-url">Base URL</label>
            <div className="row" style={{ gap: 8 }}>
              <input id="api-def-base-url" readOnly value={baseUrl} />
              <button className="btn secondary" type="button" onClick={copy}>
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
          </div>
          <div className="row" style={{ gap: 8, marginTop: 12, flexWrap: "wrap" }}>
            <button
              className="btn"
              type="button"
              onClick={() => download(`${extension.id}-openapi.json`, document)}
            >
              Download OpenAPI file
            </button>
            <a
              className="btn secondary"
              href={extension.openapi_url}
              target="_blank"
              rel="noreferrer"
            >
              Open file
            </a>
          </div>
          <div className="subtle" style={{ marginTop: 8, fontSize: 12 }}>
            Import the file into Postman, Insomnia, or a client generator. Tools that need YAML can
            read this JSON file. Example calls read your token from the AESPA_TOKEN environment
            variable.
          </div>
          {document.info?.description ? (
            <details className="api-def-intro">
              <summary>How to use this API</summary>
              <div className="subtle api-def-description">{document.info.description}</div>
            </details>
          ) : null}
          {groups.map(([tag, operations]) => (
            <div key={tag} className="api-def-group">
              <div className="extension-subsection-title">{tag}</div>
              {operations.map((item) => (
                <Operation
                  key={`${item.method} ${item.path}`}
                  document={document}
                  baseUrl={baseUrl}
                  method={item.method}
                  path={item.path}
                  operation={item.operation}
                />
              ))}
            </div>
          ))}
          {callbacks.length ? (
            <div className="api-def-group">
              <div className="extension-subsection-title">Callback events</div>
              <div className="subtle api-def-note" style={{ marginBottom: 8 }}>
                AESPA sends each event as a POST request to the scan&apos;s callback URL.
              </div>
              {callbacks.map(([name, item]) => (
                <Operation
                  key={name}
                  document={document}
                  baseUrl={baseUrl}
                  method="post"
                  path={name}
                  operation={item.post}
                  isEvent
                />
              ))}
            </div>
          ) : null}
          <DataObjects document={document} />
        </>
      ) : null}
    </section>
  );
}
