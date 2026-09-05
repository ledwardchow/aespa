export const DEFAULT_VALIDATOR_FORM = {
  enabled: true,
  max_steps: 20,
  min_severity: "low",
  end_scan_max_concurrent: 4,
  auto_validate_inline: true,
  require_concrete_disproof: true,
};

export function validatorToForm(cfg) {
  return {
    enabled: cfg.enabled ?? true,
    max_steps: cfg.max_steps ?? 20,
    min_severity: cfg.min_severity ?? "low",
    end_scan_max_concurrent: cfg.end_scan_max_concurrent ?? 4,
    auto_validate_inline: cfg.auto_validate_inline ?? true,
    require_concrete_disproof: cfg.require_concrete_disproof ?? true,
  };
}

export function validatorPayload(form) {
  return {
    enabled: form.enabled,
    max_steps: Number(form.max_steps),
    min_severity: form.min_severity,
    end_scan_max_concurrent: Number(form.end_scan_max_concurrent),
    auto_validate_inline: form.auto_validate_inline,
    require_concrete_disproof: form.require_concrete_disproof,
  };
}
