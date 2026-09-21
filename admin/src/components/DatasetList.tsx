import {
  ChevronRight,
  Clock3,
  Database,
  Loader2,
  TriangleAlert,
  XCircle,
} from 'lucide-react';
import { errorMessage } from '../api/client';
import { useDatasets, type Category, type Dataset } from '../api/datasets';

/** Categories are structural — one per pair, fixed set. */
const CATEGORY_DOT: Record<Category, string> = {
  simple: 'bg-indigo-500',
  reasoning: 'bg-cyan-400',
  multi_context: 'bg-amber-400',
  conditional: 'bg-violet-400',
};

const CATEGORIES = Object.keys(CATEGORY_DOT) as Category[];

function ago(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days >= 14) return `${Math.floor(days / 7)} weeks ago`;
  if (days >= 1) return `${days} day${days > 1 ? 's' : ''} ago`;
  return 'today';
}

const shell = 'rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center';

export default function DatasetList({ onOpen }: { onOpen: (id: string) => void }) {
  const { data, isLoading, error, refetch, isFetching } = useDatasets();

  if (isLoading) {
    return (
      <section className={`${shell} flex items-center justify-center gap-2 text-sm text-slate-400`}>
        <Loader2 size={15} className="animate-spin" /> Loading datasets…
      </section>
    );
  }

  if (error) {
    return (
      <section className={shell}>
        <p className="flex items-center justify-center gap-2 text-sm text-red-600">
          <TriangleAlert size={15} /> {errorMessage(error)}
        </p>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="mt-3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
        >
          {isFetching ? 'Retrying…' : 'Try again'}
        </button>
      </section>
    );
  }

  if (!data?.items.length) {
    return (
      <section className={shell}>
        <Database size={22} className="mx-auto text-slate-300" />
        <p className="mt-2 text-sm font-medium text-slate-600">No datasets yet</p>
        <p className="mt-0.5 text-xs text-slate-400">
          Generate one from a .zip of text files to start evaluating.
        </p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <ul className="divide-y divide-slate-100">
        {data.items.map((dataset) => (
          <Row key={dataset.id} dataset={dataset} onOpen={onOpen} />
        ))}
      </ul>
    </section>
  );
}

function Row({ dataset, onOpen }: { dataset: Dataset; onOpen: (id: string) => void }) {
  const { status, fileCount, parsedCount, pairCount } = dataset;

  if (status === 'failed') {
    return (
      <li className="flex items-center gap-4 px-5 py-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-900">{dataset.name}</p>
          <p className="mt-0.5 text-xs text-red-500">
            Failed · {dataset.error ?? 'generation did not finish'}
          </p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">
          <XCircle size={12} /> Failed
        </span>
      </li>
    );
  }

  if (status !== 'ready') {
    const percent = fileCount ? Math.round((parsedCount / fileCount) * 100) : 0;
    return (
      <li className="px-5 py-4">
        <div className="flex items-center gap-4">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-900">{dataset.name}</p>
            <p className="mt-0.5 text-xs text-slate-400">
              {status === 'pending'
                ? 'Queued · reading the archive'
                : `Generating · ${pairCount} pairs · ${parsedCount} of ${fileCount} files parsed`}
            </p>
          </div>
          <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
            <Clock3 size={12} /> {status === 'pending' ? 'Queued' : 'Running'}
          </span>
        </div>
        <div className="mt-3 h-1.5 rounded-full bg-slate-100">
          <div
            className="h-1.5 rounded-full bg-indigo-500 transition-all"
            style={{ width: `${percent}%` }}
          />
        </div>
      </li>
    );
  }

  return (
    <li
      onClick={() => onOpen(dataset.id)}
      className="cursor-pointer px-5 py-4 hover:bg-slate-50"
    >
      <div className="flex items-center gap-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-900">{dataset.name}</p>
          <p className="mt-0.5 truncate text-xs text-slate-400">
            {pairCount} pairs · {fileCount} files
            {dataset.model ? ` · ${dataset.model.name}` : ''} · {ago(dataset.createdAt)}
          </p>
        </div>
        <div className="hidden w-48 shrink-0 sm:block">
          <div className="flex h-1.5 overflow-hidden rounded-full bg-slate-100">
            {CATEGORIES.map((c) => (
              <span
                key={c}
                className={CATEGORY_DOT[c]}
                style={{ width: `${dataset.mix[c] ?? 0}%` }}
              />
            ))}
          </div>
          <p className="mt-1 truncate text-[11px] text-slate-400">
            {dataset.labels.join(', ') || 'no labels'}
          </p>
        </div>
        <ChevronRight size={16} className="text-slate-300" />
      </div>
    </li>
  );
}
