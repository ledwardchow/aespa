const COVERAGE_MODE_LABELS = {
  track: "Quick",
  standard: "Standard",
  enforce: "Full",
  deep: "Deep",
  team: "Team",
  sast_validate: "Check SAST leads only",
};

export const coverageModeLabel = (mode) => COVERAGE_MODE_LABELS[mode] || COVERAGE_MODE_LABELS.track;
