import { useState } from 'react';
import {
  CheckCircle2,
  ChevronRight,
  Clock3,
  FlaskConical,
  Loader2,
  Play,
  TriangleAlert,
  XCircle,
} from 'lucide-react';
import ExperimentForm from './ExperimentForm';
import { errorMessage } from '../api/client';
import { useDatasets } from '../api/datasets';
import { useExperiments, type Experiment } from '../api/experiments';
import { useModels } from '../api/models';
import { formatRelative } from '../utils/format';

const shell = 'rounded-2xl border border-slate-200 bg-white px-5 py-10 text-center';

const pill = 'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium';

export default function ExperimentList({
  datasetId = null,
  onOpen,
}: {
  datasetId?: string | null;
  onOpen?: (id: string) => void;
}) {
  const { data, isLoading, error, refetch, isFetching } = useExperiments(1, 20, datasetId);
  const { data: datasets } = useDatasets();
  const [newExperiment, setNewExperiment] = useState(false);

  if (isLoading) {
    return (
      <section className={`${shell} flex items-center justify-center gap-2 text-sm text-slate-400`}>
        <Loader2 size={15} className="animate-spin" /> Loading experiments…
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
      <>
        <section className={shell}>
          <FlaskConical size={22} className="mx-auto text-slate-300" />
          <p className="mt-2 text-sm font-medium text-slate-600">No experiments yet</p>
          <p className="mt-0.5 text-xs text-slate-400">
            Run a configuration against a ready dataset to score it.
          </p>
          <button
            onClick={() => setNewExperiment(true)}
            className="mx-auto mt-3 flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Play size={16} /> Run experiment
          </button>
        </section>
        <ExperimentForm
          open={newExperiment}
          onOpenChange={setNewExperiment}
          fixedValues={datasetId ? { datasetId } : {}}
        />
      </>
    );
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <ul className="divide-y divide-slate-100">
        {data.items.map((experiment) => (
          <Row
            key={experiment.id}
            experiment={experiment}
            dataset={datasets?.items.find((d) => d.id === experiment.datasetId)?.name ?? '—'}
            onOpen={onOpen}
          />
        ))}
      </ul>
    </section>
  );
}

function Row({
  experiment,
  dataset,
  onOpen,
}: {
  experiment: Experiment;
  dataset: string;
  onOpen?: (id: string) => void;
}) {
  const { status, retrievalConfig: config } = experiment;
  const { data: embeddingModels } = useModels(1, 'bi-encoder', 100);
  const setup = [
    config.indexTypes
      .map((t) =>
        t.type === 'bm25'
          ? 'BM25'
          : (embeddingModels?.items.find((m) => m.id === t.modelId)?.name ?? t.modelId),
      )
      .join(' + '),
    `top ${config.topK ?? '—'}`,
    config.rerankOn ? `rerank ${config.rerankOn}` : 'no rerank',
    formatRelative(new Date(experiment.createdAt).getTime()),
  ].join(' · ');

  if (status === 'failed') {
    return (
      <li className="flex items-center gap-4 px-5 py-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-900">{dataset}</p>
          <p className="mt-0.5 truncate text-xs text-red-500">
            Failed · {experiment.error ?? 'the run did not finish'}
          </p>
        </div>
        <span className={`${pill} bg-red-50 text-red-700`}>
          <XCircle size={12} /> Failed
        </span>
      </li>
    );
  }

  if (status !== 'success') {
    const [stage, label] = {
      pending: ['Queued', 'Queued'],
      importing: ['Importing files', 'Importing'],
      running: ['Scoring', 'Running'],
    }[status];
    return (
      <li className="flex items-center gap-4 px-5 py-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-900">{dataset}</p>
          <p className="mt-0.5 truncate text-xs text-slate-400">
            {stage} · {setup}
          </p>
        </div>
        <span className={`${pill} bg-indigo-50 text-indigo-700`}>
          <Clock3 size={12} /> {label}
        </span>
      </li>
    );
  }

  return (
    <li
      onClick={onOpen && (() => onOpen(experiment.id))}
      className={`flex items-center gap-4 px-5 py-4 ${
        onOpen ? 'cursor-pointer hover:bg-slate-50' : ''
      }`}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-900">{dataset}</p>
        <p className="mt-0.5 truncate text-xs text-slate-400">
          {setup} · {experiment.metrics.length} metrics
        </p>
      </div>
      <span className={`${pill} bg-green-50 text-green-700`}>
        <CheckCircle2 size={12} /> Ready
      </span>
      {onOpen && <ChevronRight size={16} className="text-slate-300" />}
    </li>
  );
}
