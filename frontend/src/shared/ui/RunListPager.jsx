import styles from "./RunListPager.module.css";

export function RunListPager({ page, pageSize, total, onPageChange, onPageSizeChange }) {
  if (total === 0) return null;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className={styles.pager}>
      <span aria-live="polite">
        {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
      </span>
      <label>
        Runs per page
        <select value={pageSize} onChange={(event) => onPageSizeChange(Number(event.target.value))}>
          {[10, 25, 50, 100].map((size) => (
            <option key={size} value={size}>
              {size}
            </option>
          ))}
        </select>
      </label>
      <button
        className="btn secondary sm"
        type="button"
        disabled={page === 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </button>
      <span>
        Page {page} of {pageCount}
      </span>
      <button
        className="btn secondary sm"
        type="button"
        disabled={page >= pageCount}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </button>
    </div>
  );
}
