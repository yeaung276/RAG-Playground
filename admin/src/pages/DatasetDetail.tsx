import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ChevronDown,
  FlaskConical,
  Loader2,
  Play,
  TriangleAlert,
} from 'lucide-react';
import Header from '../components/Header';
import ExperimentForm from '../components/ExperimentForm';
import ExperimentList from '../components/ExperimentList';
import ScoreBoard from '../components/ScoreBoard';
import Spec from '../components/Spec';
import PairTags from '../components/PairTags';
import Pager from '../components/Pager';
import { CATEGORIES, CATEGORY_DOT, UNTAGGED } from '../components/categories';
import { errorMessage } from '../api/client';
import {
  useDataset,
  useDatasetPairs,
  type Category,
  type DatasetPair,
} from '../api/datasets';

const filter = 'rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600';

const PAGE_SIZE = 10;

const TABS = [
  { id: 'data', label: 'Data' },
  { id: 'experiments', label: 'Experiments' },
] as const;

type Tab = (typeof TABS)[number]['id'];

function ago(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days >= 14) return `${Math.floor(days / 7)} weeks ago`;
  if (days >= 1) return `${days} day${days > 1 ? 's' : ''} ago`;
  return 'today';
}

const shell = 'rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center';

/** The pairs are the content here; composition and settings are context above them. */
export default function DatasetDetail() {
  const navigate = useNavigate();
  const { id = '' } = useParams();
  const dataset = useDataset(id);
  const pairs = useDatasetPairs(id);

  const [category, setCategory] = useState<Category | 'any'>('any');
  const [label, setLabel] = useState('any');
  const [page, setPage] = useState(0);
  const [newExperiment, setNewExperiment] = useState(false);
  const [tab, setTab] = useState<Tab>('data');

  const all = useMemo(() => pairs.data ?? [], [pairs.data]);

  // Both breakdowns count what was actually generated, not what was asked for.
  const byCategory = useMemo(
    () =>
      CATEGORIES.map(
        (c) => [c, all.filter((p) => p.category === c).length] as [Category, number],
      ),
    [all],
  );

  const byLabel = useMemo(() => {
    const names = [...(dataset.data?.labels ?? [])];
    const counts = names.map(
      (name) => [name, all.filter((p) => p.labels.includes(name)).length] as [string, number],
    );
    const untagged = all.filter((p) => p.labels.length === 0).length;
    return untagged ? [...counts, [UNTAGGED, untagged] as [string, number]] : counts;
  }, [all, dataset.data?.labels]);

  const shown = all.filter(
    (p) =>
      (category === 'any' || p.category === category) &&
      (label === 'any' ||
        (label === UNTAGGED ? p.labels.length === 0 : p.labels.includes(label))),
  );

  // The pairs arrive as one file, so paging is a slice — clamped in case a
  // filter change leaves the current page past the end.
  const pageCount = Math.max(1, Math.ceil(shown.length / PAGE_SIZE));
  const current = Math.min(page, pageCount - 1);
  const start = current * PAGE_SIZE;
  const visible = shown.slice(start, start + PAGE_SIZE);

  const error = dataset.error ?? pairs.error;
  const loading = dataset.isLoading || pairs.isLoading;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header>
        <FlaskConical size={18} className="text-indigo-600" />
        <h1 className="truncate text-base font-semibold">Evaluation</h1>
      </Header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-5 flex items-center gap-3">
          <button
            onClick={() => navigate('/evaluation')}
            className="flex size-8 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-base font-semibold text-slate-900">
              {dataset.data?.name ?? '—'}
            </h2>
            <p className="text-xs text-slate-400">
              {dataset.data
                ? `${dataset.data.pairCount} pairs · ${dataset.data.fileCount} files · generated ${ago(dataset.data.createdAt)}`
                : 'Loading…'}
            </p>
          </div>
        </div>

        <div className="mb-4 flex gap-1 border-b border-slate-200">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`-mb-px border-b-2 px-3 py-2.5 text-sm font-medium transition ${
                tab === t.id
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading ? (
          <section
            className={`${shell} flex items-center justify-center gap-2 text-sm text-slate-400`}
          >
            <Loader2 size={15} className="animate-spin" /> Loading dataset…
          </section>
        ) : error ? (
          <section className={shell}>
            <p className="flex items-center justify-center gap-2 text-sm text-red-600">
              <TriangleAlert size={15} /> {errorMessage(error)}
            </p>
            <button
              onClick={() => {
                dataset.refetch();
                pairs.refetch();
              }}
              className="mt-3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
            >
              Try again
            </button>
          </section>
        ) : tab === 'experiments' ? (
          <>
            <ScoreBoard
              datasetId={id}
              onOpen={(experimentId) => navigate(`/evaluation/experiments/${experimentId}`)}
            />
            <ExperimentList
              datasetId={id}
              onOpen={(experimentId) => navigate(`/evaluation/experiments/${experimentId}`)}
            />
          </>
        ) : (
          <>
            <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-5">
              <div className="mb-5 flex items-center justify-between gap-3 border-b border-slate-100 pb-4">
                <h3 className="text-sm font-semibold text-slate-900">Composition</h3>
                <button
                  onClick={() => setNewExperiment(true)}
                  className="flex shrink-0 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  <Play size={16} /> Run experiment
                </button>
              </div>

              <div className="grid gap-6 sm:grid-cols-2">
                <div>
                  <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Categories
                  </h3>
                  <div className="mb-2.5 flex h-2 overflow-hidden rounded-full bg-slate-100">
                    {byCategory.map(([name, count]) => (
                      <span
                        key={name}
                        className={CATEGORY_DOT[name]}
                        style={{ width: `${all.length ? (count / all.length) * 100 : 0}%` }}
                      />
                    ))}
                  </div>
                  <ul className="space-y-1.5 text-xs">
                    {byCategory.map(([name, count]) => (
                      <li key={name} className="flex items-center gap-2">
                        <span className={`size-2 shrink-0 rounded-full ${CATEGORY_DOT[name]}`} />
                        <span className="text-slate-600">{name}</span>
                        <span className="ml-auto tabular-nums text-slate-400">{count}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Labels
                  </h3>
                  {byLabel.length ? (
                    <ul className="space-y-2 text-xs">
                      {byLabel.map(([name, count]) => (
                        <li key={name} className="flex items-center gap-2.5">
                          <span className="w-28 shrink-0 truncate text-slate-600">{name}</span>
                          <span className="h-1.5 flex-1 rounded-full bg-slate-100">
                            <span
                              className="block h-1.5 rounded-full bg-slate-400"
                              style={{
                                width: `${all.length ? (count / all.length) * 100 : 0}%`,
                              }}
                            />
                          </span>
                          <span className="w-6 shrink-0 text-right tabular-nums text-slate-400">
                            {count}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-400">No labels on this dataset.</p>
                  )}
                </div>
              </div>

              <div className="mt-5 border-t border-slate-100 pt-4">
                <Spec
                  items={[
                    ['Generator', dataset.data?.model?.name ?? '—'],
                    ['Provider', dataset.data?.model?.provider ?? '—'],
                    ['Pairs per file', String(dataset.data?.samplePerFile ?? '—')],
                    ['Files', String(dataset.data?.fileCount ?? '—')],
                    ['Pairs', String(dataset.data?.pairCount ?? '—')],
                    ['Created', dataset.data ? ago(dataset.data.createdAt) : '—'],
                  ]}
                />
              </div>
            </div>

            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3.5">
                <h3 className="mr-auto text-sm font-semibold text-slate-900">Pairs</h3>
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
                <select
                  className={filter}
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                >
                  <option value="any">any label</option>
                  {byLabel.map(([name]) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
              </div>

              {shown.length ? (
                <>
                  <ul className="divide-y divide-slate-100">
                    {visible.map((pair, i) => (
                      <Pair key={`${pair.source_file}-${start + i}`} pair={pair} />
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
                  {all.length ? 'No pair matches these filters.' : 'This dataset has no pairs.'}
                </p>
              )}
            </section>
          </>
        )}
      </main>

      <ExperimentForm
        open={newExperiment}
        onOpenChange={setNewExperiment}
        fixedValues={{ datasetId: id }}
      />
    </div>
  );
}

function Pair({ pair }: { pair: DatasetPair }) {
  const [open, setOpen] = useState(false);

  return (
    <li className="px-5 py-4 hover:bg-slate-50">
      <p className="text-sm font-medium text-slate-900">{pair.question}</p>
      <p className="mt-1 border-l-2 border-slate-200 pl-3 text-sm text-slate-500">{pair.answer}</p>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
        <PairTags category={pair.category} labels={pair.labels} />
        <span className="truncate text-slate-400">{pair.source_file}</span>
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1 font-medium text-indigo-600 hover:text-indigo-700"
        >
          <ChevronDown size={12} className={open ? 'rotate-180' : undefined} />
          {open ? 'Hide context' : 'Show context'}
        </button>
      </div>

      {open && (
        <p className="mt-2.5 whitespace-pre-wrap rounded-lg bg-slate-50 px-3 py-2.5 text-xs leading-relaxed text-slate-600">
          {pair.context}
        </p>
      )}
    </li>
  );
}
