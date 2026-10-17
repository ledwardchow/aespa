import { useState } from "react";

const PAGE_SIZE = 10;

export function usePagedRows(rows) {
  const [page, setPage] = useState(0);
  const pageCount = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const start = current * PAGE_SIZE;
  return {
    rows: rows.slice(start, start + PAGE_SIZE),
    pager:
      rows.length > PAGE_SIZE ? (
        <div className="plan-usage-pager">
          <span aria-live="polite">
            {start + 1}–{Math.min(start + PAGE_SIZE, rows.length)} of {rows.length}
          </span>
          <button
            className="btn secondary sm"
            type="button"
            disabled={current === 0}
            onClick={() => setPage(current - 1)}
          >
            Previous
          </button>
          <button
            className="btn secondary sm"
            type="button"
            disabled={current >= pageCount - 1}
            onClick={() => setPage(current + 1)}
          >
            Next
          </button>
        </div>
      ) : null,
  };
}
