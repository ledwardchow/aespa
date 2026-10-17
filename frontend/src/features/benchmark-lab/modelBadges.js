export function modelBadges(model) {
  const badges = (model?.daybreak_programs || [])
    .filter((program) => ["daybreak_blue", "daybreak_red"].includes(program))
    .map((program) => (program === "daybreak_blue" ? "Daybreak Blue" : "Daybreak Red"));
  if (model?.provider === "claude_cli" && model.model === "claude-mythos-5") {
    badges.push("Glasswing");
  }
  return badges;
}
