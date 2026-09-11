export function profileLabel(profile) {
  if (!profile) return "Unknown profile";
  return `${profile.name}${profile.default_model_name ? ` · ${profile.default_model_name}` : ""}`;
}

export function SastModelSelector({ run, profiles, disabled, saving, onChange }) {
  const activeProfile = profiles.find((profile) => profile.is_active);
  return (
    <label className="sast-model-selector">
      <span>Model</span>
      <select
        className="select"
        aria-label="SAST model profile"
        value={run.llm_profile_id || ""}
        disabled={disabled || saving}
        onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
        title={
          disabled
            ? "Stop the scan before changing its model profile"
            : "Model profile used by the next SAST scan"
        }
      >
        <option value="">
          Global active{activeProfile ? ` · ${profileLabel(activeProfile)}` : ""}
        </option>
        {profiles.map((profile) => (
          <option key={profile.id} value={profile.id}>
            {profileLabel(profile)}
          </option>
        ))}
      </select>
      {saving && <em>Saving…</em>}
    </label>
  );
}
