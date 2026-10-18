import { useId, useState } from "react";

import styles from "./SiteForm.module.css";

const pathOf = (url) => {
  try {
    const parsed = new URL(url);
    return `${parsed.pathname}${parsed.hash}` || "/";
  } catch {
    return url;
  }
};

export function SiteWorkflowsTab({ workflows, onChange }) {
  const [open, setOpen] = useState(() => (workflows.length === 1 ? 0 : null));
  const update = (index, changes) =>
    onChange(workflows.map((item, i) => (i === index ? { ...item, ...changes } : item)));

  return (
    <div className={styles.panelBody}>
      <p className="subtle">
        Values saved by earlier crawls. The crawler reuses them to reach pages behind forms. Use
        test data only. Saved values are sent to the crawler model and the site.
      </p>
      {workflows.length === 0 && <div className="subtle">No saved workflows.</div>}
      <div className={styles.workflowList}>
        {workflows.map((item, index) => (
          <WorkflowItem
            key={index}
            item={item}
            open={open === index}
            onToggle={() => setOpen(open === index ? null : index)}
            onShow={() => setOpen(index)}
            onChange={(changes) => update(index, changes)}
            onRemove={() => {
              onChange(workflows.filter((_, i) => i !== index));
              setOpen(null);
            }}
          />
        ))}
      </div>
    </div>
  );
}

function WorkflowItem({ item, open, onToggle, onShow, onChange, onRemove }) {
  const id = useId();
  return (
    <div className={`${styles.workflowItem}${open ? ` ${styles.selected}` : ""}`}>
      <button
        type="button"
        className={styles.workflowHeader}
        aria-expanded={open}
        aria-controls={`${id}-body`}
        onClick={onToggle}
      >
        <span aria-hidden="true">{open ? "▾" : "▸"}</span>
        <span className={styles.accountName}>{item.name || "Unnamed workflow"}</span>
        <span className={styles.accountMeta}>{pathOf(item.start_url)}</span>
      </button>
      <div
        id={`${id}-body`}
        className={styles.workflowBody}
        hidden={!open}
        onInvalidCapture={onShow}
      >
        <div className="field">
          <label htmlFor={`${id}-name`}>Workflow name</label>
          <input
            id={`${id}-name`}
            type="text"
            required
            maxLength={100}
            value={item.name}
            onChange={(e) => onChange({ name: e.target.value })}
          />
        </div>
        <div className={styles.twoCol}>
          <div className="field">
            <label htmlFor={`${id}-goal`}>Page or form to reach</label>
            <input
              id={`${id}-goal`}
              type="text"
              required
              maxLength={220}
              value={item.goal}
              onChange={(e) => onChange({ goal: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor={`${id}-url`}>Starting page URL</label>
            <input
              id={`${id}-url`}
              type="url"
              required
              value={item.start_url}
              onChange={(e) => onChange({ start_url: e.target.value })}
            />
          </div>
        </div>
        <div className="field">
          <label htmlFor={`${id}-instructions`}>Sample data or instructions</label>
          <textarea
            id={`${id}-instructions`}
            required
            maxLength={4000}
            rows={4}
            value={item.instructions}
            onChange={(e) => onChange({ instructions: e.target.value })}
          />
        </div>
        <div className={styles.editorActions}>
          <button type="button" className="btn ghost sm" onClick={onRemove}>
            Remove workflow
          </button>
        </div>
      </div>
    </div>
  );
}
