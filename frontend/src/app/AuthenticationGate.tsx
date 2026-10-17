import { useEffect, useState, useSyncExternalStore, type FormEvent, type ReactNode } from "react";
import {
  getAuthState,
  initializeAuth,
  refreshAuthSession,
  signIn,
  subscribeAuth,
} from "../shared/auth/session.ts";
import styles from "./AuthenticationGate.module.css";

export function AuthenticationGate({ children }: { children: ReactNode }) {
  const auth = useSyncExternalStore(subscribeAuth, getAuthState);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    void initializeAuth();
  }, []);
  useEffect(() => {
    if (auth.status === "loading") {
      delete document.documentElement.dataset.aespaAuthenticated;
      return;
    }
    document.documentElement.dataset.aespaAuthenticated =
      auth.status === "signed-in" ? "true" : "false";
    if (auth.status !== "signed-in") return;
    const check = () => {
      if (!document.hidden) void refreshAuthSession().catch(() => {});
    };
    const timer = window.setInterval(check, 60_000);
    window.addEventListener("focus", check);
    document.addEventListener("visibilitychange", check);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", check);
      document.removeEventListener("visibilitychange", check);
    };
  }, [auth.status]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(key.trim());
      setKey("");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not sign in.");
    } finally {
      setBusy(false);
    }
  }

  if (auth.status === "signed-in") return children;
  return (
    <main className={styles.page}>
      <div className={styles.panel}>
        <h1 className={styles.brand} aria-label="AESPA">
          <img src="/logo-transparent.png" alt="" />
          <span aria-hidden="true">ESPA</span>
        </h1>
        {auth.status === "loading" ? (
          <p role="status">Checking authentication...</p>
        ) : (
          <form onSubmit={submit}>
            <h2>Sign in</h2>
            <p>The authentication key is shown in the AESPA console on startup.</p>
            {auth.message && !error ? <p role="status">{auth.message}</p> : null}
            <div className="field">
              <label htmlFor="authentication-key">Authentication key</label>
              <input
                id="authentication-key"
                type="password"
                autoComplete="current-password"
                required
                value={key}
                onChange={(event) => setKey(event.target.value)}
              />
            </div>
            {error ? (
              <p className="alert error" role="alert">
                {error}
              </p>
            ) : null}
            <button className="btn" type="submit" disabled={busy || !key.trim()}>
              {busy ? "Signing in..." : "Sign in"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
