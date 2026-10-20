// Names for API token permissions, shared by the token list, the token form,
// and the endpoint list so each permission reads the same everywhere.
export const API_PERMISSIONS = [
  { value: "sast", label: "SAST scans" },
  { value: "web", label: "Web scans" },
  { value: "sites", label: "Sites" },
];

// Which scans a token can see through the API.
export const SCAN_ACCESS = [
  { value: "own", label: "Only scans it creates" },
  { value: "all", label: "All scans in AESPA" },
];

export function permissionLabels(values = []) {
  return values
    .map((value) => API_PERMISSIONS.find((item) => item.value === value)?.label || value)
    .join(", ");
}
