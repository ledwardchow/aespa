export function scanType(runKind, scanModels) {
  if (runKind === "sast") return "SAST";
  return scanModels?.sast?.length ? "DAST with SAST Leads" : "DAST";
}

export function scanModelLabel(runKind, scanModels) {
  const model = scanModels?.primary;
  if (!model) return "Unavailable";
  if (model.name && model.model && model.name !== model.model)
    return `${model.name} (${model.model})`;
  return model.model || model.name || "Unavailable";
}
