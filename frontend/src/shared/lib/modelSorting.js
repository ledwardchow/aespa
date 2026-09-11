const modelCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

export function sortModelNames(models) {
  return [...(models || [])].sort((left, right) => modelCollator.compare(left, right));
}

export function sortModelConfigs(models) {
  return [...(models || [])].sort((left, right) => {
    const leftLabel = `${left.name || ""} (${left.model || ""})`;
    const rightLabel = `${right.name || ""} (${right.model || ""})`;
    return modelCollator.compare(leftLabel, rightLabel);
  });
}
