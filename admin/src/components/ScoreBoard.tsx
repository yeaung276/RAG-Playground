import { useState } from 'react';
import Tooltip from './Tooltip';
import { METRICS, METRIC_LABELS, useScoreBoard, type Metric } from '../api/experiments';
import { formatDateTime } from '../utils/format';

// Fixed per metric so a line keeps its color when others are hidden.
const COLORS: Record<Metric, string> = {
  context_precision: '#2a78d6',
  context_recall: '#eb6834',
  hit_rate: '#1baf7a',
  mrr: '#eda100',
};

const TICKS = [0, 0.25, 0.5, 0.75, 1];

const MAX_X_LABELS = 12;

export default function ScoreBoard({
  datasetId,
  onOpen,
}: {
  datasetId: string;
  onOpen: (id: string) => void;
}) {
  const { data: runs } = useScoreBoard(datasetId);
  const [hidden, setHidden] = useState<Set<Metric>>(new Set());

  if (!runs?.length) return null;

  const metrics = METRICS.filter((m) => runs.some((r) => r.scores[m] != null));
  const shown = metrics.filter((m) => !hidden.has(m));
  const points = (m: Metric) =>
    runs.flatMap((r, i) => {
      const score = r.scores[m];
      return score == null ? [] : [{ i, score }];
    });
  const x = (i: number) => `${((i + 0.5) / runs.length) * 100}%`;
  const y = (score: number) => `${(1 - score) * 100}%`;
  const labelEvery = Math.ceil(runs.length / MAX_X_LABELS);
  const toggle = (m: Metric) =>
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(m)) next.delete(m);
      else next.add(m);
      return next;
    });

  return (
    <section className="mb-4 rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900">Scores over runs</h3>
        <div className="flex flex-wrap gap-1">
          {metrics.map((m) => {
            const pts = points(m);
            const latest = pts[pts.length - 1]?.score;
            return (
              <button
                key={m}
                onClick={() => toggle(m)}
                className={`flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-slate-600 hover:bg-slate-50 ${hidden.has(m) ? 'opacity-40' : ''}`}
              >
                <span className="h-0.5 w-3 rounded-full" style={{ background: COLORS[m] }} />
                {METRIC_LABELS[m]}
                {latest != null && (
                  <span className="font-medium tabular-nums text-slate-900">
                    {latest.toFixed(2)}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="relative mb-6 ml-9 h-52">
        {TICKS.map((t) => (
          <span
            key={t}
            style={{ top: y(t) }}
            className="absolute -left-9 w-7 -translate-y-1/2 text-right text-[10px] tabular-nums text-slate-400"
          >
            {t}
          </span>
        ))}

        {runs.map((r, i) => (
          <div
            key={r.id}
            style={{ left: `${(i / runs.length) * 100}%`, width: `${100 / runs.length}%` }}
            className="absolute inset-y-0"
          >
            <Tooltip
              className="group h-full"
              content={
                <div className="space-y-1">
                  <p className="font-medium">{r.name}</p>
                  <p className="text-slate-300">{formatDateTime(r.createdAt)}</p>
                  {shown.map((m) => {
                    const score = r.scores[m];
                    return score == null ? null : (
                      <p key={m} className="flex items-center gap-2">
                        <span className="h-0.5 w-3 rounded-full" style={{ background: COLORS[m] }} />
                        <span className="font-semibold tabular-nums">{score.toFixed(2)}</span>
                        <span className="text-slate-300">{METRIC_LABELS[m]}</span>
                      </p>
                    );
                  })}
                </div>
              }
            >
              <button
                aria-label={r.name}
                onClick={() => onOpen(r.id)}
                className="relative h-full w-full cursor-pointer"
              >
                <span className="absolute inset-y-0 left-1/2 w-px bg-slate-300 opacity-0 group-hover:opacity-100" />
              </button>
            </Tooltip>
            {i % labelEvery === 0 && (
              <span className="absolute left-1/2 top-full mt-1.5 -translate-x-1/2 whitespace-nowrap text-[10px] text-slate-400">
                {r.name.slice(r.name.lastIndexOf('#'))}
              </span>
            )}
          </div>
        ))}

        <svg className="pointer-events-none absolute inset-0 size-full overflow-visible">
          {TICKS.map((t) => (
            <line
              key={t}
              x1="0"
              x2="100%"
              y1={y(t)}
              y2={y(t)}
              className={t === 0 ? 'stroke-slate-200' : 'stroke-slate-100'}
            />
          ))}
          {shown.map((m) => {
            const pts = points(m);
            return (
              <g key={m} stroke={COLORS[m]} fill={COLORS[m]}>
                {pts.slice(1).map((p, k) => (
                  <line
                    key={p.i}
                    x1={x(pts[k].i)}
                    y1={y(pts[k].score)}
                    x2={x(p.i)}
                    y2={y(p.score)}
                    strokeWidth={2}
                    strokeLinecap="round"
                  />
                ))}
                {pts.map((p) => (
                  <circle key={p.i} cx={x(p.i)} cy={y(p.score)} r={5} stroke="white" strokeWidth={2} />
                ))}
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
}
