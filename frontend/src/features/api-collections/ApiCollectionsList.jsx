import * as apiCollectionsApi from "../../shared/api/apiCollections.js";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";

import { nav } from "../../shared/navigation/router.js";
import { IconPlus } from "../../shared/ui/Icons.jsx";
import { EmptyState } from "../../shared/ui/EmptyState.jsx";
import { PageHeader } from "../../shared/ui/PageHeader.jsx";

export function ApiCollectionsList() {
  const [collections, setCollections] = useState(null);
  const [error, setError] = useState(null);
  const [importing, setImporting] = useState(false);
  const [sortField, setSortField] = useState("name");
  const [sortDir, setSortDir] = useState("asc");
  const importRef = useRef(null);

  const load = useCallback(async () => {
    try {
      setCollections(await apiCollectionsApi.listApiCollections());
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const sortArrow = (field) => {
    if (sortField !== field) return null;
    return (
      <span style={{ marginLeft: "4px", fontSize: "10px", opacity: 0.85 }}>
        {sortDir === "asc" ? "▲" : "▼"}
      </span>
    );
  };

  const sortedCollections = useMemo(() => {
    if (!collections) return [];
    return [...collections].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === "endpoint_count") {
        valA = a.endpoint_count || 0;
        valB = b.endpoint_count || 0;
      } else if (sortField === "document_count") {
        valA = a.document_count || 0;
        valB = b.document_count || 0;
      }

      if (valA == null) valA = "";
      if (valB == null) valB = "";

      let cmp =
        typeof valA === "number" && typeof valB === "number"
          ? valA - valB
          : String(valA).localeCompare(String(valB), undefined, {
              sensitivity: "base",
              numeric: true,
            });
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [collections, sortField, sortDir]);

  const onDelete = async (c) => {
    if (
      !confirm(`Delete "${c.name}"? This also removes all uploaded docs, endpoints and test runs.`)
    )
      return;
    try {
      await apiCollectionsApi.deleteApiCollection(c.id);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const onExport = (c) => {
    window.location.href = `/api/api-collections/${c.id}/export`;
  };

  const onImportFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    e.target.value = "";
    setImporting(true);
    setError(null);
    try {
      await apiCollectionsApi.importApiCollection(await file.text());
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <>
      <PageHeader
        title="APIs"
        actions={
          <>
            <input
              ref={importRef}
              type="file"
              accept=".json"
              style={{
                display: "none",
              }}
              onChange={onImportFile}
            />
            <button
              className="btn secondary"
              onClick={() => importRef.current.click()}
              disabled={importing}
            >
              {importing ? "Importing…" : "Import API"}
            </button>
            <button className="btn" onClick={() => nav("#/apis/new")}>
              <IconPlus /> New API collection
            </button>
          </>
        }
      />
      <div className="content scroll-content">
        {error && (
          <div
            className="alert error"
            style={{
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}
        {collections === null && <div className="subtle">Loading…</div>}
        {collections !== null && collections.length === 0 && (
          <EmptyState
            title="No API collections yet"
            sub="Create a collection, upload API docs, and run structured API security tests."
            action={
              <button className="btn" onClick={() => nav("#/apis/new")}>
                <IconPlus /> New API collection
              </button>
            }
          />
        )}
        {collections && collections.length > 0 && (
          <div className="table-wrap">
            <table>
              <colgroup>
                <col
                  style={{
                    width: "20%",
                  }}
                />
                <col
                  style={{
                    width: "38%",
                  }}
                />
                <col
                  style={{
                    width: "10%",
                  }}
                />
                <col
                  style={{
                    width: "10%",
                  }}
                />
                <col
                  style={{
                    width: "22%",
                  }}
                />
              </colgroup>
              <thead>
                <tr>
                  <th
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => toggleSort("name")}
                  >
                    Name {sortArrow("name")}
                  </th>
                  <th
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => toggleSort("base_url")}
                  >
                    Base URL {sortArrow("base_url")}
                  </th>
                  <th
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => toggleSort("endpoint_count")}
                  >
                    Endpoints {sortArrow("endpoint_count")}
                  </th>
                  <th
                    style={{ cursor: "pointer", userSelect: "none" }}
                    onClick={() => toggleSort("document_count")}
                  >
                    Files {sortArrow("document_count")}
                  </th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {sortedCollections.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <a
                        href={`#/apis/${c.id}`}
                        style={{
                          fontWeight: 600,
                        }}
                      >
                        {c.name}
                      </a>
                    </td>
                    <td className="url">{c.base_url}</td>
                    <td>
                      {c.endpoint_count > 0 ? c.endpoint_count : <span className="subtle">—</span>}
                    </td>
                    <td>
                      {c.document_count > 0 ? c.document_count : <span className="subtle">—</span>}
                    </td>
                    <td>
                      <div
                        className="row"
                        style={{
                          justifyContent: "flex-end",
                        }}
                      >
                        <button className="btn secondary sm" onClick={() => nav(`#/apis/${c.id}`)}>
                          Open
                        </button>
                        <button className="btn secondary sm" onClick={() => onExport(c)}>
                          Export
                        </button>
                        <button className="btn danger-outline sm" onClick={() => onDelete(c)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
