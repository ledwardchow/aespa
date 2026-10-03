import { useId, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import styles from "./SiteSummary.module.css";
import { CheckboxSelector } from "./CheckboxSelector.jsx";
import { paretoFrontier } from "./paretoFrontier.js";
import { linearFit } from "./linearFit.js";
import { scanType } from "./scanPresentation.js";
import { placeSingleScanLabels, placeTrendLabels } from "./trendLabels.js";

const shortModelName = (model) => {
  const name = model?.name || model?.model;
  const basename = name?.split("/").at(-1);
  if (!basename) return "Unknown model";
  let start = 0;
  for (let index = 0; index < basename.length; index += 1) {
    // Dots between digits are model versions, such as qwen3.8 or claude-4.5.
    if (
      basename[index] === "." &&
      !(/\d/.test(basename[index - 1]) && /\d/.test(basename[index + 1]))
    ) {
      start = index + 1;
    }
  }
  return basename.slice(start) || "Unknown model";
};
const modelName = (result) => shortModelName(result.scan_models?.primary);

const money = (value) =>
  value == null ? "Cost unavailable" : `$${value.toFixed(value > 0 && value < 0.01 ? 4 : 2)}`;
const SCAN_TYPES = ["DAST", "DAST with SAST Leads", "SAST"];
const SCAN_TRENDS = {
  DAST: { color: "#75a7ff", dash: "2 4" },
  "DAST with SAST Leads": { color: "#f2b56b", dash: "10 4" },
  SAST: { color: "#9ac96c", dash: "10 3 2 3" },
};
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

function Point({
  shape,
  x,
  y,
  color,
  label,
  onOpen,
  onShowDetails,
  onHideDetails,
  describedBy,
  opacity,
  optimal,
}) {
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
      aria-describedby={describedBy}
      onMouseEnter={onShowDetails}
      onMouseLeave={onHideDetails}
      onFocus={onShowDetails}
      onBlur={onHideDetails}
      className="benchmark-chart-point"
      style={{ opacity }}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
    >
      {optimal && (
        <circle cx={x} cy={y} r="12" fill="none" stroke="var(--text)" strokeWidth="1.5" />
      )}
      {symbol}
    </g>
  );
}

export function SiteSummary({ results, onOpen, siteSelector, showChart = true }) {
  const [axis, setAxis] = useState("cost");
  const [display, setDisplay] = useState("optimal");
  const tooltipId = useId();
  const plotClipId = useId();
  const [kinds, setKinds] = useState({ DAST: true, "DAST with SAST Leads": true, SAST: true });
  const [modelVisibility, setModelVisibility] = useState({});
  const [hovered, setHovered] = useState(null);
  const [hoveredLegend, setHoveredLegend] = useState(null);
  const [focusedLegend, setFocusedLegend] = useState(null);
  const graphResults = useMemo(
    () => results.filter((result) => result.summary.full + result.summary.partial > 0),
    [results],
  );
  const models = useMemo(() => [...new Set(graphResults.map(modelName))].sort(), [graphResults]);
  const defaultVisibleModels = useMemo(() => {
    const counts = new Map();
    for (const result of results) {
      const name = modelName(result);
      counts.set(name, (counts.get(name) || 0) + 1);
    }
    const optimal = new Set(
      paretoFrontier(
        graphResults.map((result) => ({
          name: modelName(result),
          x: result.scan_cost_usd,
          y: result.summary.full + result.summary.partial,
        })),
      ).map((point) => point.name),
    );
    return new Set(models.filter((name) => counts.get(name) > 1 || optimal.has(name)));
  }, [results, graphResults, models]);
  const excludedModels = models.filter(
    (name) => !(modelVisibility[name] ?? defaultVisibleModels.has(name)),
  );
  const selectedLegend = hoveredLegend || focusedLegend;
  const activeLegend =
    (selectedLegend?.kind === "model" && excludedModels.includes(selectedLegend.name)) ||
    (selectedLegend?.kind === "kind" && !kinds[selectedLegend.name])
      ? null
      : selectedLegend;
  const legendEvents = (kind, name) => ({
    onPointerEnter: () => setHoveredLegend({ kind, name }),
    onPointerLeave: () => {
      setHoveredLegend(null);
      setFocusedLegend(null);
    },
    onFocus: () => setFocusedLegend({ kind, name }),
    onBlur: () => setFocusedLegend(null),
  });
  const pointMatchesLegend = (result) =>
    !activeLegend ||
    (activeLegend.kind === "model"
      ? modelName(result) === activeLegend.name
      : scanType(result.run_kind, result.scan_models) === activeLegend.name);
  const showDetails = (event, result) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    setHovered({
      result,
      left: Math.max(8, Math.min(bounds.right + 12, window.innerWidth - 328)),
      top: Math.max(8, Math.min(bounds.top, window.innerHeight - 250)),
    });
  };
  const trendModels = models.filter((name) => !excludedModels.includes(name));
  const modelColor = (name) => MODEL_COLORS[models.indexOf(name) % MODEL_COLORS.length];
  const visible = graphResults.filter(
    (result) =>
      kinds[scanType(result.run_kind, result.scan_models)] &&
      !excludedModels.includes(modelName(result)),
  );
  const axisValue = (result) =>
    axis === "cost"
      ? result.scan_cost_usd
      : result.scan_started_at
        ? new Date(result.scan_started_at).getTime()
        : NaN;
  const plotted = visible.filter((result) => Number.isFinite(axisValue(result)));
  const frontier =
    display === "optimal" && axis === "cost"
      ? paretoFrontier(
          plotted.map((result) => ({
            id: result.id,
            name: modelName(result),
            x: result.scan_cost_usd,
            y: result.summary.full + result.summary.partial,
          })),
        )
      : [];
  const optimalIds = new Set(frontier.map((point) => point.id));
  const optimalModels = new Set(frontier.map((point) => point.name));
  const unavailable = visible.filter((result) => !Number.isFinite(axisValue(result)));
  const fits = new Map(
    models.map((name) => [
      name,
      linearFit(
        plotted
          .filter((result) => modelName(result) === name)
          .map((result) => ({
            x: axisValue(result),
            y: result.summary.full + result.summary.partial,
          })),
      ),
    ]),
  );
  const kindFits = new Map(
    SCAN_TYPES.map((type) => [
      type,
      linearFit(
        plotted
          .filter((result) => scanType(result.run_kind, result.scan_models) === type)
          .map((result) => ({
            x: axisValue(result),
            y: result.summary.full + result.summary.partial,
          })),
      ),
    ]),
  );
  const values = plotted.map(axisValue);
  let minValue = axis === "cost" ? 0 : Math.min(...values);
  let maxValue = axis === "cost" ? Math.max(0.01, ...values) : Math.max(...values);
  if (axis === "date" && minValue === maxValue) {
    minValue -= 1800000;
    maxValue += 1800000;
  }
  const formatAxis = (value) =>
    axis === "cost"
      ? money(value)
      : new Date(value).toLocaleString(undefined, {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
  const axisLabel = axis === "cost" ? "Scan cost (USD)" : "Scan start date and time";
  const maxFindings = Math.max(
    1,
    ...plotted.map((result) => result.summary.full + result.summary.partial),
  );
  const findingTicks =
    maxFindings <= 4
      ? Array.from({ length: maxFindings + 1 }, (_, index) => index)
      : [...new Set([0, 0.25, 0.5, 0.75, 1].map((fraction) => Math.round(maxFindings * fraction)))];
  const plot = { left: 70, right: 750, top: 25, bottom: 285 };
  const x = (value) =>
    plot.left + ((value - minValue) / (maxValue - minValue)) * (plot.right - plot.left);
  const y = (count) => plot.bottom - (count / maxFindings) * (plot.bottom - plot.top);
  const trends = (display === "model" ? trendModels : []).flatMap((name) => {
    const fit = fits.get(name);
    return fit
      ? [
          {
            name,
            color: modelColor(name),
            dash: "6 4",
            start: { x: x(fit.start.x), y: y(fit.start.y) },
            end: { x: x(fit.end.x), y: y(fit.end.y) },
          },
        ]
      : [];
  });
  for (const type of display === "scan-type" ? SCAN_TYPES : []) {
    const fit = kindFits.get(type);
    if (kinds[type] && fit) {
      trends.push({
        name: type,
        isCategory: true,
        ...SCAN_TRENDS[type],
        start: { x: x(fit.start.x), y: y(fit.start.y) },
        end: { x: x(fit.end.x), y: y(fit.end.y) },
      });
    }
  }
  const scanPoints = plotted.map((result) => ({
    name: modelName(result),
    x: x(axisValue(result)),
    y: y(result.summary.full + result.summary.partial),
  }));
  const trendLabels = placeTrendLabels(trends, scanPoints, plot);
  const optimalSegment = frontier
    .slice(1)
    .map((point, index) => ({
      name: "Optimal",
      start: { x: x(frontier[index].x), y: y(frontier[index].y) },
      end: { x: x(point.x), y: y(point.y) },
    }))
    .toSorted(
      (a, b) =>
        Math.hypot(b.end.x - b.start.x, b.end.y - b.start.y) -
        Math.hypot(a.end.x - a.start.x, a.end.y - a.start.y),
    )[0];
  const optimalLabel = optimalSegment
    ? placeTrendLabels([optimalSegment], scanPoints, plot).get("Optimal")
    : null;
  const optimalModelLabels = placeSingleScanLabels(scanPoints, trends, trendLabels, plot, {
    labelPoints: [
      ...new Map(
        frontier.map((point) => [
          point.name,
          {
            name: point.name,
            x: x(point.x),
            y: y(point.y),
          },
        ]),
      ).values(),
    ],
    ensureAll: true,
  });
  const singleScanLabels = placeSingleScanLabels(scanPoints, trends, trendLabels, plot);
  const pointLabels = new Map([
    ...[...singleScanLabels].filter(([name]) => !optimalModels.has(name)),
    ...optimalModelLabels,
  ]);

  return (
    <div className={styles.summary}>
      <div className={styles.filterBar}>
        {siteSelector}
        <CheckboxSelector
          label="Scan type"
          options={SCAN_TYPES}
          onSelectAll={(checked) =>
            setKinds(Object.fromEntries(SCAN_TYPES.map((type) => [type, checked])))
          }
          selected={SCAN_TYPES.filter((type) => kinds[type])}
          onToggle={(type, checked) => setKinds((current) => ({ ...current, [type]: checked }))}
        />
        <CheckboxSelector
          label="Model"
          options={models}
          onSelectAll={(checked) =>
            setModelVisibility(Object.fromEntries(models.map((name) => [name, checked])))
          }
          selected={models.filter((name) => !excludedModels.includes(name))}
          onToggle={(name, checked) =>
            setModelVisibility((current) => ({ ...current, [name]: checked }))
          }
        />
        <label className={styles.selector}>
          Compare by
          <select
            className="select"
            value={axis}
            onChange={(event) => {
              setAxis(event.target.value);
              if (event.target.value !== "cost" && display === "optimal") setDisplay("model");
              setHovered(null);
            }}
          >
            <option value="cost">Scan cost</option>
            <option value="date">Scan date</option>
          </select>
        </label>
      </div>
      {showChart && (
        <section className={`card benchmark-chart-card ${styles.chartCard}`}>
          <div className={`benchmark-chart-header ${styles.chartHeader}`}>
            <div>
              <h2>{axis === "cost" ? "Scan cost and findings" : "Scan date and findings"}</h2>
              {display === "optimal" && (
                <p className="subtle">
                  Best findings for cost across visible scans. Outlined points and marked models are
                  on the line.
                </p>
              )}
            </div>
            <label className={styles.selector}>
              Display
              <select
                className="select"
                aria-label="Display"
                value={display}
                onChange={(event) => {
                  setDisplay(event.target.value);
                  setHoveredLegend(null);
                  setFocusedLegend(null);
                  if (event.target.value === "optimal") setAxis("cost");
                  setHovered(null);
                }}
              >
                <option value="model">By Model</option>
                <option value="scan-type">By Scan Type</option>
                <option value="optimal">Optimal</option>
              </select>
            </label>
          </div>
          {results.length === 0 ? (
            <p className="subtle">No analyses have been saved for this Site.</p>
          ) : (
            <>
              {plotted.length ? (
                <div className={styles.plot}>
                  <svg
                    viewBox="0 0 800 340"
                    role="img"
                    aria-label={`${axis === "cost" ? "Scan cost" : "Scan date"} versus full and partial findings`}
                    className={`benchmark-chart ${styles.chart}`}
                  >
                    <defs>
                      <clipPath id={plotClipId}>
                        <rect
                          x={plot.left}
                          y={plot.top}
                          width={plot.right - plot.left}
                          height={plot.bottom - plot.top}
                        />
                      </clipPath>
                    </defs>
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
                        <text
                          x={x(minValue + (maxValue - minValue) * fraction)}
                          y={plot.bottom + 20}
                          textAnchor="middle"
                        >
                          {formatAxis(minValue + (maxValue - minValue) * fraction)}
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
                      {axisLabel}
                    </text>
                    <text transform="translate(17 155) rotate(-90)" textAnchor="middle">
                      Full + partial findings
                    </text>
                    {trends.map((trend) => {
                      const { name } = trend;
                      const label = trendLabels.get(name);
                      return (
                        <g
                          key={`${trend.isCategory ? "kind" : "model"}:${name}`}
                          role="img"
                          aria-label={`${name}${trend.isCategory ? " scan type" : ""} linear trend`}
                          className={styles.trend}
                          style={{
                            opacity:
                              !activeLegend ||
                              (activeLegend.kind === (trend.isCategory ? "kind" : "model") &&
                                activeLegend.name === name)
                                ? 1
                                : 0.15,
                          }}
                        >
                          <line
                            x1={label?.lineStart.x ?? trend.start.x}
                            y1={label?.lineStart.y ?? trend.start.y}
                            x2={label?.lineEnd.x ?? trend.end.x}
                            y2={label?.lineEnd.y ?? trend.end.y}
                            stroke={trend.color}
                            strokeWidth={trend.isCategory ? "2.5" : "2"}
                            strokeDasharray={trend.dash}
                            clipPath={`url(#${plotClipId})`}
                          />
                          {label && (
                            <text
                              x={label.x}
                              y={label.y}
                              textAnchor="middle"
                              dominantBaseline="central"
                              transform={`rotate(${label.angle} ${label.x} ${label.y})`}
                              style={{ fill: trend.color, fontSize: label.fontSize }}
                            >
                              {name}
                            </text>
                          )}
                        </g>
                      );
                    })}
                    {frontier.length > 0 && (
                      <g
                        role="img"
                        aria-label="Optimal: best findings for cost"
                        className={styles.trend}
                        style={{ opacity: activeLegend ? 0.15 : 1 }}
                      >
                        <polyline
                          points={frontier.map((point) => `${x(point.x)},${y(point.y)}`).join(" ")}
                          fill="none"
                          stroke="var(--text)"
                          strokeWidth="2.5"
                          strokeLinejoin="round"
                          clipPath={`url(#${plotClipId})`}
                        />
                        {optimalLabel && (
                          <text
                            x={optimalLabel.x}
                            y={optimalLabel.y}
                            textAnchor="middle"
                            dominantBaseline="central"
                            transform={`rotate(${optimalLabel.angle} ${optimalLabel.x} ${optimalLabel.y})`}
                            style={{ fill: "var(--text)", fontSize: optimalLabel.fontSize }}
                          >
                            Optimal
                          </text>
                        )}
                      </g>
                    )}
                    {plotted.map((result) => (
                      <Point
                        key={result.id}
                        shape={SCAN_TYPES.indexOf(scanType(result.run_kind, result.scan_models))}
                        x={x(axisValue(result))}
                        y={y(result.summary.full + result.summary.partial)}
                        color={modelColor(modelName(result))}
                        opacity={pointMatchesLegend(result) ? 1 : 0.15}
                        optimal={optimalIds.has(result.id)}
                        label={`${optimalIds.has(result.id) ? "Optimal, " : ""}${result.run_name}, ${scanType(result.run_kind, result.scan_models)}, ${modelName(result)}, ${money(result.scan_cost_usd)}, ${result.summary.full + result.summary.partial} findings`}
                        onOpen={() => {
                          setHovered(null);
                          onOpen(result.id);
                        }}
                        onShowDetails={(event) => showDetails(event, result)}
                        onHideDetails={() => setHovered(null)}
                        describedBy={hovered?.result.id === result.id ? tooltipId : undefined}
                      />
                    ))}
                    {[...pointLabels].map(([name, label]) => (
                      <g
                        key={name}
                        data-guide-label={name}
                        className={styles.singleScanLabel}
                        style={{
                          opacity: plotted.some(
                            (result) => modelName(result) === name && pointMatchesLegend(result),
                          )
                            ? 1
                            : 0.15,
                        }}
                      >
                        <line
                          x1={label.pointX}
                          y1={label.pointY}
                          x2={label.edgeX}
                          y2={label.edgeY}
                          stroke="var(--panel)"
                          strokeWidth="4.5"
                          strokeLinecap="round"
                        />
                        <line
                          x1={label.pointX}
                          y1={label.pointY}
                          x2={label.edgeX}
                          y2={label.edgeY}
                          stroke={modelColor(name)}
                          strokeWidth="1.3"
                          strokeLinecap="round"
                        />
                        <circle
                          cx={label.pointX}
                          cy={label.pointY}
                          r="3"
                          fill={modelColor(name)}
                          stroke="var(--panel)"
                          strokeWidth="1.5"
                        />
                        <text
                          x={label.x}
                          y={label.y}
                          textAnchor="middle"
                          dominantBaseline="central"
                          style={{ fill: modelColor(name) }}
                          aria-label={`${name}${optimalModels.has(name) ? " optimal model" : " single scan"}`}
                        >
                          {name}
                        </text>
                      </g>
                    ))}
                  </svg>
                </div>
              ) : (
                <p className="subtle">
                  No analyses with findings and a recorded{" "}
                  {axis === "cost" ? "scan cost" : "scan start time"} match these filters.
                </p>
              )}
              {unavailable.length > 0 && (
                <p className="subtle">
                  {unavailable.length} matching{" "}
                  {unavailable.length === 1 ? "analysis has" : "analyses have"} no recorded{" "}
                  {axis === "cost" ? "scan cost" : "scan start time"}
                  and cannot be plotted.
                </p>
              )}
              <div className="benchmark-chart-legend" aria-label="Scan type legend">
                {SCAN_TYPES.map((type) => (
                  <button
                    key={type}
                    {...legendEvents("kind", type)}
                    type="button"
                    className={styles.modelLegend}
                    aria-pressed={kinds[type]}
                    title={`${kinds[type] ? "Hide" : "Show"} ${type}`}
                    onClick={() => {
                      setKinds((current) => ({ ...current, [type]: !current[type] }));
                      setHoveredLegend(null);
                      setFocusedLegend(null);
                    }}
                  >
                    <span
                      className={`benchmark-shape benchmark-shape-${SCAN_TYPES.indexOf(type)}`}
                      style={{ background: SCAN_TRENDS[type].color }}
                    />
                    {type}
                  </button>
                ))}
              </div>
              <div className="benchmark-chart-legend" aria-label="Model legend">
                {models.map((name) => (
                  <button
                    key={name}
                    {...legendEvents("model", name)}
                    aria-label={`${name}${optimalModels.has(name) ? ", Optimal" : ""}`}
                    type="button"
                    className={`${styles.modelLegend} ${styles.modelVisibility}`}
                    aria-pressed={!excludedModels.includes(name)}
                    title={`${excludedModels.includes(name) ? "Show" : "Hide"} ${name}`}
                    onClick={() => {
                      setModelVisibility((current) => ({
                        ...current,
                        [name]: excludedModels.includes(name),
                      }));
                      setHoveredLegend(null);
                      setFocusedLegend(null);
                    }}
                  >
                    <span
                      className="benchmark-shape benchmark-shape-0"
                      style={{ backgroundColor: modelColor(name) }}
                    />
                    {name}
                    {optimalModels.has(name) && (
                      <span className={styles.optimalBadge}>Optimal</span>
                    )}
                  </button>
                ))}
              </div>
            </>
          )}
        </section>
      )}
      {showChart &&
        hovered &&
        visible.some((result) => result.id === hovered.result.id) &&
        createPortal(
          <div
            id={tooltipId}
            role="tooltip"
            className={styles.tooltip}
            style={{ left: hovered.left, top: hovered.top }}
          >
            <strong>{hovered.result.run_name}</strong>
            <span className={styles.tooltipType}>
              {scanType(hovered.result.run_kind, hovered.result.scan_models)}
              {hovered.result.run_id ? ` · Scan #${hovered.result.run_id}` : ""}
            </span>
            <dl>
              <dt>Model</dt>
              <dd>{modelName(hovered.result)}</dd>
              {hovered.result.scan_models?.primary?.provider && (
                <>
                  <dt>Provider</dt>
                  <dd>{hovered.result.scan_models.primary.provider}</dd>
                </>
              )}
              {hovered.result.scan_started_at && (
                <>
                  <dt>Started</dt>
                  <dd>{new Date(hovered.result.scan_started_at).toLocaleString()}</dd>
                </>
              )}
              <dt>Cost</dt>
              <dd>{money(hovered.result.scan_cost_usd)}</dd>
              <dt>Findings</dt>
              <dd>
                {hovered.result.summary.full} full · {hovered.result.summary.partial} partial
              </dd>
            </dl>
            {hovered.result.run_kind !== "sast" &&
              (hovered.result.scan_models?.sast || []).map((source) => (
                <div key={source.run_id} className={styles.tooltipSource}>
                  <span>
                    SAST{source.run_name ? `: ${source.run_name}` : ` scan #${source.run_id}`}
                  </span>
                  <strong>{shortModelName(source.model)}</strong>
                </div>
              ))}
            <span className={styles.tooltipHint}>Click to open analysis</span>
          </div>,
          document.body,
        )}
    </div>
  );
}

export { modelName, money };
