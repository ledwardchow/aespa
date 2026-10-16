import { line, max, scaleLinear, scaleTime } from "d3";
import { useEffect, useRef, useState } from "react";

import { fmtPercent, fmtTime, fmtUsd } from "./format.js";

const HEIGHT = 220;
const BAR_HEIGHT = 70;
const MARGIN = { top: 10, right: 16, bottom: 24, left: 44 };

function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(720);
  useEffect(() => {
    const node = ref.current;
    if (!node || typeof globalThis.ResizeObserver === "undefined") return undefined;
    const observer = new globalThis.ResizeObserver(([entry]) => {
      setWidth(Math.max(320, Math.floor(entry.contentRect.width)));
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

export function UsageChart({ timeline, readings }) {
  const [ref, width] = useWidth();
  const start = new Date(timeline.start);
  const end = new Date(timeline.end);
  const inRange = (value) => {
    const time = new Date(value);
    return time >= start && time <= end;
  };
  const shownReadings = readings.filter((row) => inRange(row.observed_at));
  const lines = timeline.lines
    .map((points) => points.filter((point) => inRange(point.t)))
    .filter((points) => points.length > 1);
  const highest = max([
    ...shownReadings.map((row) => row.used_percent),
    ...lines.flat().map((point) => point.percent),
    0,
  ]);
  const top = Math.min(100, Math.max(10, Math.ceil((highest * 1.15) / 10) * 10));

  const x = scaleTime()
    .domain([start, end])
    .range([MARGIN.left, width - MARGIN.right]);
  const y = scaleLinear()
    .domain([0, top])
    .range([HEIGHT - MARGIN.bottom, MARGIN.top]);
  const path = line()
    .x((point) => x(new Date(point.t)))
    .y((point) => y(point.percent));

  const buckets = timeline.buckets;
  const priced = buckets.some((bucket) => bucket.cost_usd != null);
  const value = (bucket) =>
    priced ? bucket.cost_usd || 0 : bucket.input_tokens + bucket.output_tokens;
  const barTop = max(buckets, value) || 0;
  const barY = scaleLinear()
    .domain([0, barTop || 1])
    .range([BAR_HEIGHT - 4, 4]);
  const xTicks = x.ticks(Math.max(2, Math.floor(width / 140)));
  const tickFormat = x.tickFormat();

  return (
    <div ref={ref} className="plan-usage-chart">
      <svg width={width} height={HEIGHT} role="img" aria-label="Usage % over time">
        {y.ticks(5).map((tick) => (
          <g key={tick}>
            <line
              className="plan-usage-grid"
              x1={MARGIN.left}
              x2={width - MARGIN.right}
              y1={y(tick)}
              y2={y(tick)}
            />
            <text className="plan-usage-axis" x={MARGIN.left - 6} y={y(tick) + 4} textAnchor="end">
              {tick}%
            </text>
          </g>
        ))}
        {xTicks.map((tick) => (
          <text
            key={tick.getTime()}
            className="plan-usage-axis"
            x={x(tick)}
            y={HEIGHT - 6}
            textAnchor="middle"
          >
            {tickFormat(tick)}
          </text>
        ))}
        {lines.map((points) => (
          <path key={points[0].t} className="plan-usage-line" d={path(points)} />
        ))}
        {shownReadings.map((row) => (
          <circle
            key={row.id}
            className="plan-usage-dot"
            cx={x(new Date(row.observed_at))}
            cy={y(row.used_percent)}
            r={4}
          >
            <title>{`${fmtPercent(row.used_percent)} at ${fmtTime(row.observed_at)}`}</title>
          </circle>
        ))}
      </svg>
      <div className="plan-usage-bar-label subtle">
        {priced ? "AESPA usage at API prices" : "AESPA tokens (input + output)"}
        {barTop
          ? ` · highest ${priced ? fmtUsd(barTop) : Math.round(barTop).toLocaleString()}`
          : ""}
      </div>
      <svg width={width} height={BAR_HEIGHT} role="img" aria-label="AESPA usage over time">
        {buckets.map((bucket) => {
          const left = x(new Date(bucket.start));
          const right = x(new Date(bucket.end));
          const amount = value(bucket);
          if (!amount) return null;
          return (
            <rect
              key={bucket.start}
              className="plan-usage-bar"
              x={left + 1}
              width={Math.max(1, right - left - 2)}
              y={barY(amount)}
              height={BAR_HEIGHT - 4 - barY(amount)}
            >
              <title>
                {`${fmtTime(bucket.start)}: ${priced ? fmtUsd(bucket.cost_usd) : `${amount.toLocaleString()} tokens`}`}
              </title>
            </rect>
          );
        })}
      </svg>
    </div>
  );
}
