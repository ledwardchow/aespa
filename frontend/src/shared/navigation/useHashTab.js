import { useCallback, useSyncExternalStore } from "react";

const subscribe = (callback) => {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
};

const getHash = () => window.location.hash;

export function useHashTab(name, allowed, fallback) {
  const hash = useSyncExternalStore(subscribe, getHash, () => "");
  const [, query = ""] = hash.split("?", 2);
  const selected = new URLSearchParams(query).get(name);
  const value = allowed.includes(selected) ? selected : fallback;

  const setValue = useCallback(
    (next) => {
      const [path, search = ""] = window.location.hash.split("?", 2);
      const params = new URLSearchParams(search);
      params.set(name, next);
      window.location.hash = `${path}?${params}`;
    },
    [name],
  );

  return [value, setValue];
}
