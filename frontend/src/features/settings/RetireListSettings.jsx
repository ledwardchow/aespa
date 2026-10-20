import * as settingsApi from "../../shared/api/settings.js";
import { useState, useEffect } from "react";
import { PolicySettings } from "./ScannerPolicySettings.jsx";
import styles from "./RetireListSettings.module.css";
import { fmtDate } from "../../shared/lib/dates.js";
import { PageError } from "../../shared/ui/Notice.jsx";

const REFRESH_MESSAGES = {
  updated: "Downloaded the latest list.",
  unchanged: "Already up to date.",
};

function RetireListStatus() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        setStatus(await settingsApi.getRetireListStatus());
      } catch (e) {
        setError(e.message);
      }
    })();
  }, []);

  const onRefresh = async () => {
    setError(null);
    setMessage(null);
    setRefreshing(true);
    try {
      const result = await settingsApi.refreshRetireList();
      setStatus(result);
      if (result.status === "failed") {
        setError(`Could not download the latest list: ${result.error || "unknown error"}`);
      } else {
        setMessage(REFRESH_MESSAGES[result.status] || "Done.");
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className={`card ${styles.statusCard}`}>
      <div className="form-section-title">Vulnerable JavaScript library list</div>
      <div className="subtle" style={{ marginBottom: "10px" }}>
        Web and SAST scans check JavaScript libraries against the Retire.js list of known vulnerable
        versions.
      </div>
      {!status && !error && <div className="subtle">Loading…</div>}
      {status && (
        <dl className={styles.facts}>
          <dt>List in use</dt>
          <dd>{status.copy === "downloaded" ? "Downloaded copy" : "Copy included with AESPA"}</dd>
          <dt>Last updated</dt>
          <dd>{fmtDate(status.fetched_at)}</dd>
          <dt>Coverage</dt>
          <dd>
            {status.libraries} libraries, {status.vulnerabilities} known issues
          </dd>
          {status.skipped_patterns > 0 && (
            <>
              <dt>Skipped patterns</dt>
              <dd>
                {status.skipped_patterns} of {status.patterns} detection patterns can't be used and
                are skipped.
              </dd>
            </>
          )}
        </dl>
      )}
      <PageError error={error} inline={!status} onDismiss={() => setError(null)} />
      <div className="divider" />
      <div className="row spread">
        <div>{message && <span className="save-confirm">{message}</span>}</div>
        <button type="button" className="btn" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Downloading…" : "Refresh now"}
        </button>
      </div>
    </div>
  );
}

function RetireAutoUpdateFields({ form, upd }) {
  return (
    <>
      <div className="form-section-title">Automatic updates</div>
      <label className="toggle-row">
        <input
          type="checkbox"
          checked={!!form.retire_auto_update}
          onChange={(e) => upd({ retire_auto_update: e.target.checked })}
        />
        <span>Download the latest list when a scan starts</span>
      </label>
      <div className="subtle" style={{ marginBottom: "10px" }}>
        AESPA downloads the latest list from GitHub at most once a day. Turn this off for offline
        use; scans then use the last downloaded copy, or the copy included with AESPA.
      </div>
    </>
  );
}

export function RetireListSettings() {
  return (
    <div id="global-libraries-panel" role="tabpanel" aria-labelledby="global-libraries-tab">
      <RetireListStatus />
      <PolicySettings Fields={RetireAutoUpdateFields} />
    </div>
  );
}
