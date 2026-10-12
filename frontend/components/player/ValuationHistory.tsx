"use client";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MarketValue } from "@/lib/api/types";
import { formatDate, formatMoney, fullMoney } from "@/lib/format";
import { orderedValuations } from "@/lib/player";
export function ValuationHistory({ values }: { values: MarketValue[] }) {
  const ordered = orderedValuations(values);
  const data = ordered.map((value) => ({
    ...value,
    timestamp: Date.parse(value.value_date),
  }));
  return (
    <section
      className="pp-chart-section"
      aria-labelledby="valuation-history-title"
    >
      <div className="pp-section-title">
        <span className="eyebrow">OBSERVED, OVER TIME</span>
        <h2 id="valuation-history-title">Market value history</h2>
        <p className="pp-note">
          Recorded observations only. Connecting lines do not represent
          additional valuations.
        </p>
      </div>
      {!data.length ? (
        <p className="pp-empty">No historical valuations available.</p>
      ) : (
        <>
          <div
            className="pp-chart"
            role="group"
            aria-label={`${data.length} observed valuations from ${formatDate(ordered[0].value_date)} to ${formatDate(ordered.at(-1)!.value_date)}`}
          >
            <ResponsiveContainer
              width="100%"
              height="100%"
              minWidth={0}
              initialDimension={{ width: 240, height: 270 }}
            >
              <LineChart
                data={data}
                accessibilityLayer
                margin={{ left: 4, right: 20, top: 20, bottom: 8 }}
              >
                <CartesianGrid
                  vertical={false}
                  stroke="var(--border)"
                  strokeDasharray="3 5"
                />
                <XAxis
                  dataKey="timestamp"
                  type="number"
                  domain={["dataMin", "dataMax"]}
                  ticks={data.map((point) => point.timestamp)}
                  tickFormatter={(value) =>
                    new Date(value).getUTCFullYear().toString()
                  }
                  tick={{ fill: "var(--muted)", fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={65}
                />
                <YAxis
                  tickFormatter={(value) => formatMoney(value)}
                  tick={{ fill: "var(--muted)", fontSize: 11 }}
                  width={65}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    const point = payload?.[0]?.payload as
                      (typeof data)[number] | undefined;
                    return active && point ? (
                      <div className="pp-chart-tooltip">
                        <span>{formatDate(point.value_date)}</span>
                        <strong>{fullMoney(point.value_eur)}</strong>
                        <small>{point.source}</small>
                      </div>
                    ) : null;
                  }}
                />
                <Line
                  type="linear"
                  dataKey="value_eur"
                  stroke="var(--profile-chart)"
                  strokeWidth={2}
                  dot={{ r: 4, fill: "var(--surface)", strokeWidth: 2 }}
                  activeDot={{ r: 6 }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="pp-note">
            {data.length} stored observations ·{" "}
            {formatMoney(ordered[0].value_eur)} on{" "}
            {formatDate(ordered[0].value_date)} →{" "}
            {formatMoney(ordered.at(-1)!.value_eur)} on{" "}
            {formatDate(ordered.at(-1)!.value_date)}.
          </p>
          <details className="pp-chart-data">
            <summary>View recorded values as a table</summary>
            <div className="pp-table-wrap">
              <table>
                <caption className="sr-only">
                  All recorded market values
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Date</th>
                    <th scope="col">Observed EUR</th>
                    <th scope="col">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {ordered.map((value, index) => (
                    <tr key={`${value.value_date}-${value.source}-${index}`}>
                      <td>{formatDate(value.value_date)}</td>
                      <td>{fullMoney(value.value_eur)}</td>
                      <td>{value.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}
