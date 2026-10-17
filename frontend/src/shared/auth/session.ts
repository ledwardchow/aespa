import { readResponse } from "../api/request.ts";

export type AuthSession = { authenticated: boolean; csrf_token?: string };
type AuthState =
  | { status: "loading" }
  | { status: "signed-out"; message?: string }
  | { status: "signed-in"; csrfToken: string };

let state: AuthState = { status: "loading" };
let revision = 0;
const listeners = new Set<() => void>();
let startup: Promise<void> | undefined;

export const getAuthState = () => state;
export function subscribeAuth(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function updateState(next: AuthState) {
  state = next;
  revision += 1;
  listeners.forEach((listener) => listener());
}

function acceptSession(session: AuthSession | null) {
  updateState(
    session?.authenticated && session.csrf_token
      ? { status: "signed-in", csrfToken: session.csrf_token }
      : { status: "signed-out" },
  );
}

export function isManagementPath(path: string) {
  return (
    (path.startsWith("/api/") || path.startsWith("/extension/")) &&
    !["/api/auth/session", "/api/auth/login", "/api/auth/exchange"].includes(path) &&
    !path.startsWith("/extension/aespa.api/v1/")
  );
}

export function installAuthFetch(target: Window = window) {
  const original = target.fetch.bind(target);
  target.fetch = async (input, init) => {
    const request = input instanceof Request ? input : undefined;
    const url = new URL(request?.url ?? String(input), target.location.href);
    const management = url.origin === target.location.origin && isManagementPath(url.pathname);
    const startedRevision = revision;
    let options = init;
    if (management && state.status === "signed-in") {
      const method = (init?.method ?? request?.method ?? "GET").toUpperCase();
      if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
        const headers = new Headers(init?.headers ?? request?.headers);
        if (!headers.has("Authorization")) headers.set("X-AESPA-CSRF", state.csrfToken);
        options = { ...init, headers };
      }
    }
    const response = await original(input, options);
    if (management && response.status === 401 && revision === startedRevision) {
      updateState({ status: "signed-out", message: "Sign in again to continue." });
    }
    return response;
  };
  return () => {
    target.fetch = original;
  };
}

async function authenticate(path: string, body?: object) {
  return readResponse<AuthSession>(
    await fetch(path, {
      method: body ? "POST" : "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }),
  );
}

export function initializeAuth() {
  startup ??= (async () => {
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const ticket = fragment.get("aespa-login");
    if (ticket) {
      const next = fragment.get("next");
      const route = next?.startsWith("#/") ? next : "#/";
      window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search + route,
      );
    }
    try {
      acceptSession(await authenticate("/api/auth/session"));
      if (ticket) acceptSession(await authenticate("/api/auth/exchange", { token: ticket }));
    } catch (error) {
      updateState({
        status: "signed-out",
        message: error instanceof Error ? error.message : "Could not connect to AESPA.",
      });
    }
  })();
  return startup;
}

export async function signIn(key: string) {
  acceptSession(await authenticate("/api/auth/login", { key }));
}

export async function refreshAuthSession() {
  acceptSession(await authenticate("/api/auth/session"));
}

export async function getAuthenticationKey() {
  const data = await readResponse<{ key: string }>(
    await fetch("/api/auth/key", {
      credentials: "same-origin",
      cache: "no-store",
    }),
  );
  if (!data?.key) throw new Error("Could not retrieve the authentication key.");
  return data.key;
}
