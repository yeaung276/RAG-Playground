import { useMemo, useState, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, FlaskConical, Loader2, RotateCw, Tag, XCircle } from 'lucide-react';
import Header from '../components/Header';
import Modal from '../components/Modal';
import Spec from '../components/Spec';
import PairTags from '../components/PairTags';
import Pager from '../components/Pager';
import Tooltip from '../components/Tooltip';
import { CATEGORIES, CATEGORY_DOT, UNTAGGED } from '../components/categories';
import { indexTypeName } from '../api/config';
import { useDataset, type Category } from '../api/datasets';
import {
  METRIC_LABELS,
  METRICS,
  useBestScores,
  useExperiment,
  useExperimentResult,
  useRerunExperiment,
  type ExperimentResult,
  type Metric,
  type PairStatus,
} from '../api/experiments';
import { useModelName } from '../api/models';
import { formatRelative } from '../utils/format';

const filter = 'rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600';

const PAGE_SIZE = 10;

const STATUS_STYLE: Record<PairStatus, string> = {
  full: 'bg-green-50 text-green-700',
  partial: 'bg-amber-50 text-amber-700',
  miss: 'bg-red-50 text-red-700',
};

const STATUSES = Object.keys(STATUS_STYLE) as PairStatus[];

const METRIC_TONE: Record<Metric, 'cyan' | 'amber'> = {
  context_precision: 'cyan',
  context_recall: 'cyan',
  hit_rate: 'amber',
  mrr: 'amber',
};

type BreakdownRow = {
  name: string;
  pairs: number;
  score: number;
  metrics: Partial<Record<Metric, number>>;
};

/** Per-metric averages over a group of pairs; the row's score is their mean. */
function summarize(name: string, group: ExperimentResult['pairs']): BreakdownRow {
  const metrics: Partial<Record<Metric, number>> = {};
  for (const m of METRICS) {
    const scored = group.filter((p) => p.scores[m] !== undefined);
    if (scored.length) metrics[m] = scored.reduce((sum, p) => sum + p.scores[m], 0) / scored.length;
  }
  const values = Object.values(metrics);
  const score = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  return { name, pairs: group.length, score, metrics };
}

/** Hierarchy: the config it ran with, then where it moved, then each pair. */
export default function ExperimentDetail() {
  const navigate = useNavigate();
  const { id = '' } = useParams();
  const { data: experiment } = useExperiment(id);
  const failed = experiment?.status === 'failed';
  const rerun = useRerunExperiment();
  const { data: dataset } = useDataset(experiment?.datasetId ?? '');
  const modelName = useModelName();

  const kb = experiment?.kbConfig;
  const kbSpec: [string, string][] = kb
    ? [
        ['Chunking method', kb.chunkingMethod],
        ['Chunking model', kb.chunkingModelId ? modelName(kb.chunkingModelId) : '—'],
        ['Parent chunk size', String(kb.maxChunkSize)],
        ['Child chunk size', String(kb.minChunkSize)],
        ['Index types', kb.indexTypes.map((t) => indexTypeName(t, modelName)).join(' + ')],
        ['Reranker', kb.reranker ? `${modelName(kb.reranker.modelId)} · ${kb.reranker.type}` : 'off'],
        ['HyDE', kb.hyde ? modelName(kb.hyde.modelId) : 'off'],
      ]
    : [];

  const retrieval = experiment?.retrievalConfig;
  const retrievalSpec: [string, string][] = retrieval
    ? [
        ['Index types', retrieval.indexTypes.map((t) => indexTypeName(t, modelName)).join(' + ')],
        ['Top K', String(retrieval.topK ?? '—')],
        ['Rerank on', retrieval.rerankOn ?? 'off'],
        ['Rerank pool', String(retrieval.rerankPool ?? '—')],
        ['Prefetch limit', String(retrieval.prefetchLimit ?? '—')],
      ]
    : [];

  const { data: best } = useBestScores(id);
  // Metrics of both runs: one the best run lacks ticks at this run, one this run lacks fills 0.
  const meters = METRICS.filter(
    (m) => experiment?.metrics.includes(m) || best?.[m] !== undefined,
  ).map((m) => {
    const score = experiment?.scores?.[m] ?? 0;
    return { metric: m, score, best: best?.[m] ?? score };
  });

  const result = useExperimentResult(id, experiment?.status === 'success');

  const byCategory = useMemo(() => {
    const pairs = result.data?.pairs ?? [];
    return CATEGORIES.map((c) => summarize(c, pairs.filter((p) => p.category === c))).filter(
      (row) => row.pairs > 0,
    );
  }, [result.data]);

  const byLabel = useMemo(() => {
    const pairs = result.data?.pairs ?? [];
    const names = [...new Set(pairs.flatMap((p) => p.labels))];
    const rows = names.map((l) => summarize(l, pairs.filter((p) => p.labels.includes(l))));
    const untagged = pairs.filter((p) => p.labels.length === 0);
    return untagged.length ? [...rows, summarize(UNTAGGED, untagged)] : rows;
  }, [result.data]);

  const [category, setCategory] = useState<Category | 'any'>('any');
  const [label, setLabel] = useState('any');
  const [status, setStatus] = useState<PairStatus | 'any'>('any');
  const [page, setPage] = useState(0);
  const [opened, setOpened] = useState<ExperimentResult['pairs'][number] | null>(null);

  const all = result.data?.pairs ?? [];
  const shown = all.filter(
    (p) =>
      (category === 'any' || p.category === category) &&
      (label === 'any' ||
        (label === UNTAGGED ? p.labels.length === 0 : p.labels.includes(label))) &&
      (status === 'any' || p.status === status),
  );

  // Same paging as the dataset page: a slice, clamped when a filter shrinks the list.
  const pageCount = Math.max(1, Math.ceil(shown.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const start = current * PAGE_SIZE;
  const visible = shown.slice(start, start + PAGE_SIZE);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header>
        <FlaskConical size={18} className="text-indigo-600" />
        <h1 className="truncate text-base font-semibold">Evaluation</h1>
      </Header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-5 flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="flex size-8 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-base font-semibold text-slate-900">
              {experiment?.name ?? '—'}
            </h2>
            <p className="text-xs text-slate-400">
              {dataset && experiment
                ? `${dataset.pairCount} pairs · finished ${formatRelative(new Date(experiment.updatedAt).getTime())}`
                : 'Loading…'}
            </p>
          </div>
          <button
            onClick={() => rerun.mutate(id)}
            disabled={rerun.isPending}
            className="flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            <RotateCw size={14} className={rerun.isPending ? 'animate-spin' : ''} /> Rerun
          </button>
        </div>

        {/* 1 — the config, frozen when the experiment was created */}
        <section className="mb-4 grid gap-6 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2">
          <div>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Knowledge base
            </h3>
            <Spec items={kbSpec} stacked />
          </div>
          <div>
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Retrieval
            </h3>
            <Spec items={retrievalSpec} stacked />
          </div>
        </section>

        {failed ? (
          <section className="mb-4 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-5">
            <XCircle size={18} className="mt-0.5 shrink-0 text-red-600" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-red-700">Run failed</p>
              <p className="mt-1 whitespace-pre-wrap break-words text-xs text-red-600">
                {experiment?.error ?? 'The run did not finish.'}
              </p>
            </div>
          </section>
        ) : (
          <>
            {/* 2 — where it moved */}
            <section className="mb-4 rounded-2xl border border-slate-200 bg-white p-5">
              <div className="mb-4 flex items-baseline justify-between">
                <h3 className="text-sm font-semibold text-slate-900">Metrics</h3>
                <span className="text-xs text-slate-400">tick marks the best so far on this dataset</span>
              </div>

              <div className="flex flex-wrap gap-x-8 gap-y-4">
                {meters.map((m) => (
                  <Meter
                    key={m.metric}
                    label={METRIC_LABELS[m.metric]}
                    score={m.score}
                    baseline={m.best}
                    tone={METRIC_TONE[m.metric]}
                  />
                ))}
              </div>
            </section>

            <div className="mb-4 grid gap-4 lg:grid-cols-2">
              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <h3 className="border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-900">
                  By category
                </h3>
                <Breakdown rows={byCategory} dotted />
              </section>

              <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                <h3 className="flex items-center gap-2 border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-900">
                  <Tag size={15} className="text-slate-400" /> By label
                </h3>
                <Breakdown rows={byLabel} />
              </section>
            </div>

            {/* 3 — each pair */}
            <section className="mb-4 overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3.5">
                <h3 className="mr-auto text-sm font-semibold text-slate-900">Results</h3>
                <select
                  className={filter}
                  value={status}
                  onChange={(e) => setStatus(e.target.value as PairStatus | 'any')}
                >
                  <option value="any">any status</option>
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <select
                  className={filter}
                  value={category}
                  onChange={(e) => setCategory(e.target.value as Category | 'any')}
                >
                  <option value="any">any category</option>
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
                <select className={filter} value={label} onChange={(e) => setLabel(e.target.value)}>
                  <option value="any">any label</option>
                  {byLabel.map(({ name }) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>

              {result.isLoading ? (
                <p className="flex items-center justify-center gap-2 px-5 py-10 text-sm text-slate-400">
                  <Loader2 size={15} className="animate-spin" /> Downloading results…
                </p>
              ) : shown.length ? (
                <>
                  <ul className="divide-y divide-slate-100">
                    {visible.map((pair, i) => (
                      <Result key={start + i} pair={pair} onOpen={() => setOpened(pair)} />
                    ))}
                  </ul>
                  <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
                    <span>
                      {start + 1}–{start + visible.length} of {shown.length}
                    </span>
                    <Pager page={current} pageCount={pageCount} onPage={setPage} />
                  </div>
                </>
              ) : (
                <p className="px-5 py-10 text-center text-sm text-slate-400">
                  {all.length ? 'No pair matches these filters.' : 'No results yet.'}
                </p>
              )}
            </section>
          </>
        )}
      </main>

      <PairDetail pair={opened} onClose={() => setOpened(null)} />
    </div>
  );
}

/** A score against its baseline: the fill is this run, the tick is what it is being compared to. */
function Meter({
  label,
  score,
  baseline,
  tone = 'violet',
}: {
  label: string;
  score: number;
  baseline: number;
  tone?: 'violet' | 'cyan' | 'amber';
}) {
  const delta = score - baseline;
  const fill = {
    violet: 'bg-violet-500',
    cyan: 'bg-cyan-500',
    amber: 'bg-amber-500',
  }[tone];

  return (
    <div className="w-full sm:w-[calc(50%-1rem)]">
      <div className="mb-1.5 flex items-baseline gap-2 text-xs">
        <span className="font-medium text-slate-600">{label}</span>
        <span className="ml-auto tabular-nums text-slate-900">{score.toFixed(2)}</span>
        <span
          className={`w-11 text-right tabular-nums ${
            delta > 0 ? 'text-green-600' : delta < 0 ? 'text-red-600' : 'text-slate-400'
          }`}
        >
          {delta > 0 ? '+' : ''}
          {delta.toFixed(2)}
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${fill}`} style={{ width: `${score * 100}%` }} />
        <span
          className="absolute -top-0.5 h-3 w-0.5 rounded-full bg-slate-400"
          style={{ left: `${baseline * 100}%` }}
          title={`best so far ${baseline.toFixed(2)}`}
        />
      </div>
    </div>
  );
}

/** One row per group: its combined score, with each metric's average on hover. */
function Breakdown({ rows, dotted }: { rows: BreakdownRow[]; dotted?: boolean }) {
  if (!rows.length) {
    return <p className="px-5 py-6 text-center text-xs text-slate-400">No scores yet.</p>;
  }

  return (
    <ul className="divide-y divide-slate-100">
      {rows.map(({ name, pairs, score, metrics }) => (
        <li key={name}>
          <Tooltip
            className="flex items-center gap-3 px-5 py-3 text-sm hover:bg-slate-50"
            content={
              <table>
                <tbody>
                  {(Object.entries(metrics) as [Metric, number][]).map(([m, value]) => (
                    <tr key={m}>
                      <td className="pr-4 text-slate-300">{METRIC_LABELS[m]}</td>
                      <td className="text-right tabular-nums">{value.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }
          >
            {dotted && (
              <span className={`size-2 shrink-0 rounded-full ${CATEGORY_DOT[name as Category]}`} />
            )}
            <span className="min-w-0 flex-1 truncate font-medium text-slate-900">{name}</span>
            <span className="w-10 shrink-0 text-right text-xs tabular-nums text-slate-400">
              {pairs}
            </span>
            <span className="w-20 shrink-0">
              <span className="block h-1.5 rounded-full bg-slate-100">
                <span
                  className="block h-1.5 rounded-full bg-slate-400"
                  style={{ width: `${score * 100}%` }}
                />
              </span>
            </span>
            <span className="w-9 shrink-0 text-right tabular-nums text-slate-900">
              {score.toFixed(2)}
            </span>
          </Tooltip>
        </li>
      ))}
    </ul>
  );
}

function Result({
  pair,
  onOpen,
}: {
  pair: ExperimentResult['pairs'][number];
  onOpen: () => void;
}) {
  const scores = (Object.entries(pair.scores) as [Metric, number][])
    .map(([m, value]) => `${METRIC_LABELS[m]} ${value.toFixed(2)}`)
    .join(' · ');

  return (
    <li onClick={onOpen} className="flex cursor-pointer items-start gap-3 px-5 py-4 hover:bg-slate-50">
      <span
        className={`mt-0.5 w-14 shrink-0 rounded-md px-2 py-0.5 text-center text-xs font-medium ${STATUS_STYLE[pair.status]}`}
      >
        {pair.status}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900">{pair.question}</p>
        <p className="mt-1 border-l-2 border-slate-200 pl-3 text-sm text-slate-500">
          {pair.generated_answer ?? <span className="italic text-slate-400">No generated answer</span>}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px]">
          <PairTags category={pair.category as Category} labels={pair.labels} />
          <span className="tabular-nums text-slate-400">{scores}</span>
        </div>
      </div>
    </li>
  );
}

/** One pair in full: the question on top, the answers left, the golden text and what came back right. */
function PairDetail({
  pair,
  onClose,
}: {
  pair: ExperimentResult['pairs'][number] | null;
  onClose: () => void;
}) {
  const heading = 'mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400';

  return (
    <Modal
      open={!!pair}
      onOpenChange={(open) => !open && onClose()}
      title="Pair"
      subtitle={pair?.source_file}
      size="lg"
    >
      {pair && (
        <>
          <div className="border-b border-slate-200 px-5 py-4">
            <p className="text-sm font-medium text-slate-900">{pair.question}</p>
            <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
              <span className={`rounded-md px-2 py-0.5 font-medium ${STATUS_STYLE[pair.status]}`}>
                {pair.status}
              </span>
              <PairTags category={pair.category as Category} labels={pair.labels} />
            </div>
          </div>

          <div className="grid min-h-0 flex-1 md:grid-cols-2">
            <div className="space-y-5 overflow-y-auto border-slate-200 p-5 md:border-r">
              <div>
                <h4 className={heading}>Generated answer</h4>
                <p className="whitespace-pre-wrap text-sm text-slate-700">
                  {pair.generated_answer ?? (
                    <span className="italic text-slate-400">No generated answer</span>
                  )}
                </p>
              </div>
              <div>
                <h4 className={heading}>Actual answer</h4>
                <p className="whitespace-pre-wrap text-sm text-slate-700">{pair.answer}</p>
              </div>
            </div>

            <div className="space-y-5 overflow-y-auto p-5">
              <div>
                <h4 className={heading}>Golden text</h4>
                <p className="whitespace-pre-wrap rounded-lg bg-slate-50 px-3 py-2.5 text-xs leading-relaxed text-slate-600">
                  {pair.context}
                </p>
              </div>
              <div>
                <h4 className={heading}>Retrieved chunks</h4>
                <ol className="space-y-3">
                  {pair.retrieved.map((chunk) => (
                    <li key={chunk.rank} className="rounded-lg border border-slate-200 p-3">
                      <div className="mb-1.5 flex items-center gap-2 text-[11px] text-slate-400">
                        <span className="font-medium text-slate-600">#{chunk.rank}</span>
                        <span className="truncate">{chunk.source ?? '—'}</span>
                        <span className="ml-auto tabular-nums">{chunk.score.toFixed(3)}</span>
                      </div>
                      <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-600">
                        <Highlighted text={chunk.content} spans={chunk.highlights} />
                      </p>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </>
      )}
    </Modal>
  );
}

/** `text` with the given [start, end) ranges marked. */
function Highlighted({ text, spans }: { text: string; spans: [number, number][] }) {
  const parts: ReactNode[] = [];
  let at = 0;
  for (const [start, end] of spans) {
    const from = Math.max(start, at);
    if (from >= end) continue;
    parts.push(
      text.slice(at, from),
      <mark key={from} className="rounded bg-amber-100 text-slate-900">
        {text.slice(from, end)}
      </mark>,
    );
    at = end;
  }
  parts.push(text.slice(at));
  return <>{parts}</>;
}
