import { useSyncExternalStore } from "react";
import { parseRoute } from "./parseRoute.ts";
const subscribe = (callback) => {
  window.addEventListener("hashchange", callback);
  return () => window.removeEventListener("hashchange", callback);
};
const getHash = () => window.location.hash || "#/";
export function useRoute() {
  return parseRoute(useSyncExternalStore(subscribe, getHash, () => "#/"));
}
export const nav = (to) => {
  window.location.hash = to;
};
