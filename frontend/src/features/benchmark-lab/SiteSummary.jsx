import { useMemo, useState } from "react";

const modelName = (result) => {
  const model =
    result.run_kind === "sast"
      ? result.scan_models?.sast?.[0]?.model
      : result.scan_models?.test_lead;
  return model?.name || model?.model || "Unknown model";
};

const money = (value) =>
  value == null ? "Cost unavailable" : `$${value.toFixed(value > 0 && value < 0.01 ? 4 : 2)}`;
const MODEL_COLORS = [
  "#5b8def",
  "#d8894a",
  "#8fbc5a",
  "#b887d3",
  "#df6f81",
  "#49a9a0",
  "#cca345",
  "#8a98d4",
];

function Point({ shape, x, y, color, label, onOpen }) {
  const common = { fill: color, stroke: "var(--panel)", strokeWidth: 2 };
  const symbol =
    shape === 0 ? (
      <circle cx={x} cy={y} r="7" {...common} />
    ) : shape === 1 ? (
      <rect x={x - 7} y={y - 7} width="14" height="14" rx="2" {...common} />
    ) : shape === 2 ? (
      <path d={`M ${x} ${y - 9} L ${x + 9} ${y + 7} L ${x - 9} ${y + 7} Z`} {...common} />
    ) : (
      <path d={`M ${x} ${y - 9} L ${x + 9} ${y} L ${x} ${y + 9} L ${x - 9} ${y} Z`} {...common} />
    );
  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={label}
      className="benchmark-chart-point"
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
    >
      <title>{label}</title>
      {symbol}
    </g>
  );
}

export function SiteSummary({ results, onOpen }) {
  const [excludedModels, setExcludedModels] = useState([]);
  const [kinds, setKinds] = useState({ sast: true, dast: true });
  const models = useMemo(() => [...new Set(results.map(modelName))].sort(), [results]);
  const modelColor = (name) => MODEL_COLORS[models.indexOf(name) % MODEL_COLORS.length];
  const visible = results.filter(
    (result) =>
      kinds[result.run_kind === "sast" ? "sast" : "dast"] &&
      !excludedModels.includes(modelName(result)),
  );
  const plotted = visible.filter((result) => Number.isFinite(result.scan_cost_usd));
  const unavailable = visible.filter((result) => !Number.isFinite(result.scan_cost_usd));
  const maxCost = Math.max(0.01, ...plotted.map((result) => result.scan_cost_usd));
  const maxFindings = Math.max(
    1,
    ...plotted.map((result) => result.summary.full + result.summary.partial),
  );
  const findingTicks =
    maxFindings <= 4
      ? Array.from({ length: maxFindings + 1 }, (_, index) => index)
      : [...new Set([0, 0.25, 0.5, 0.75, 1].map((fraction) => Math.round(maxFindings * fraction)))];
  const plot = { left: 70, right: 750, top: 25, bottom: 285 };
  const x = (cost) => plot.left + (cost / maxCost) * (plot.right - plot.left);
  const y = (count) => plot.bottom - (count / maxFindings) * (plot.bottom - plot.top);

  return (
    <section className="card benchmark-chart-card">
      <div className="benchmark-chart-header">
        <div>
          <h2>Scan cost and findings</h2>
          <p className="subtle">
            Each point is one saved analysis. Open a point to view its findings.
          </p>
        </div>
      </div>
      {results.length === 0 ? (
        <p className="subtle">No analyses have been saved for this Site.</p>
      ) : (
        <>
          <div className="benchmark-chart-filters">
            <fieldset>
              <legend>Scan type</legend>
              {[
                ["dast", "DAST"],
                ["sast", "SAST"],
              ].map(([key, label]) => (
                <label key={key}>
                  <input
                    type="checkbox"
                    checked={kinds[key]}
                    onChange={(event) => setKinds({ ...kinds, [key]: event.target.checked })}
                  />{" "}
                  {label}
                </label>
              ))}
            </fieldset>
            <fieldset>
              <legend>Model</legend>
              {models.map((name) => (
                <label key={name}>
                  <input
                    type="checkbox"
                    checked={!excludedModels.includes(name)}
                    onChange={(event) =>
                      setExcludedModels(
                        event.target.checked
                          ? excludedModels.filter((item) => item !== name)
                          : [...excludedModels, name],
                      )
                    }
                  />{" "}
                  {name}
                </label>
              ))}
            </fieldset>
          </div>
          {plotted.length ? (
            <div className="benchmark-chart-scroll">
              <svg
                viewBox="0 0 800 340"
                role="img"
                aria-label="Scan cost versus full and partial findings"
                className="benchmark-chart"
              >
                {findingTicks.map((count) => (
                  <g key={count}>
                    <line
                      x1={plot.left}
                      x2={plot.right}
                      y1={y(count)}
                      y2={y(count)}
                      className="benchmark-chart-grid"
                    />
                    <text x={plot.left - 12} y={y(count) + 4} textAnchor="end">
                      {count}
                    </text>
                  </g>
                ))}
                {[0, 0.25, 0.5, 0.75, 1].map((fraction) => (
                  <g key={fraction}>
                    <text x={x(maxCost * fraction)} y={plot.bottom + 20} textAnchor="middle">
                      {money(maxCost * fraction)}
                    </text>
                  </g>
                ))}
                <line
                  x1={plot.left}
                  x2={plot.left}
                  y1={plot.top}
                  y2={plot.bottom}
                  className="benchmark-chart-axis"
                />
                <line
                  x1={plot.left}
                  x2={plot.right}
                  y1={plot.bottom}
                  y2={plot.bottom}
                  className="benchmark-chart-axis"
                />
                <text x="410" y="332" textAnchor="middle">
                  Scan cost (USD)
                </text>
                <text transform="translate(17 155) rotate(-90)" textAnchor="middle">
                  Full + partial findings
                </text>
                {plotted.map((result) => (
                  <Point
                    key={result.id}
                    shape={models.indexOf(modelName(result)) % 4}
                    x={x(result.scan_cost_usd)}
                    y={y(result.summary.full + result.summary.partial)}
                    color={modelColor(modelName(result))}
                    label={`${result.run_name}, ${result.run_kind === "sast" ? "SAST" : "DAST"}, ${modelName(result)}, ${money(result.scan_cost_usd)}, ${result.summary.full + result.summary.partial} findings`}
                    onOpen={() => onOpen(result.id)}
                  />
                ))}
              </svg>
            </div>
          ) : (
            <p className="subtle">No analyses with a recorded scan cost match these filters.</p>
          )}
          {unavailable.length > 0 && (
            <p className="subtle">
              {unavailable.length} matching{" "}
              {unavailable.length === 1 ? "analysis has" : "analyses have"} no recorded scan cost
              and cannot be plotted.
            </p>
          )}
          <div className="benchmark-chart-legend">
            {models
              .filter((name) => !excludedModels.includes(name))
              .map((name) => (
                <span key={name}>
                  <span
                    className={`benchmark-shape benchmark-shape-${models.indexOf(name) % 4}`}
                    style={{ backgroundColor: modelColor(name) }}
                  />
                  {name}
                </span>
              ))}
          </div>
        </>
      )}
    </section>
  );
}

export { modelName, money };
