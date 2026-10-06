import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Play } from 'lucide-react';
import {
  CHUNKING_METHODS,
  DEFAULT_CONFIG,
  type ChunkingMethod,
  type KnowledgeBaseConfig,
} from '../api/config';
import { useKnowledgeBases } from '../api/knowledge';
import { useModels } from '../api/models';
import { useDatasets } from '../api/datasets';
import { useCreateExperiment, type Metric } from '../api/experiments';
import { errorMessage } from '../api/client';

const input =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100';

const lockable = `${input} disabled:bg-slate-50 disabled:text-slate-500`;

/** A number that carries its unit inside the control and states its own range. */
function Num({
  name,
  suffix,
  min,
  max,
  step = 1,
  value,
  disabled,
  width = 'w-full',
}: {
  name?: string;
  suffix: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  disabled?: boolean;
  width?: string;
}) {
  return (
    <span
      className={`${width} flex items-center rounded-lg border border-slate-300 pr-2.5 transition focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100 ${
        disabled ? 'bg-slate-50 text-slate-500' : 'bg-white'
      }`}
    >
      <input
        type="number"
        name={name}
        defaultValue={value}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        required
        className="w-full [appearance:textfield] bg-transparent px-3 py-2 text-sm tabular-nums outline-none [&::-webkit-inner-spin-button]:appearance-none"
      />
      <span className="shrink-0 whitespace-nowrap text-xs text-slate-400">{suffix}</span>
    </span>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline gap-2">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        {hint && <span className="ml-auto text-xs text-slate-400">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

export interface ExperimentValues {
  datasetId: string;
  knowledgeId: string;
  chunkingMethod: ChunkingMethod;
  chunkingModelId: string;
  maxChunkSize: number;
  minChunkSize: number;
  indexTypes: KnowledgeBaseConfig['indexTypes'];
  topK: number;
  rerankOn: '' | 'parent' | 'child';
  rerankPool: number;
  prefetchLimit: number;
}

const VALUES: ExperimentValues = {
  datasetId: '',
  knowledgeId: '',
  chunkingMethod: DEFAULT_CONFIG.chunkingMethod,
  chunkingModelId: '',
  maxChunkSize: DEFAULT_CONFIG.maxChunkSize,
  minChunkSize: DEFAULT_CONFIG.minChunkSize,
  indexTypes: DEFAULT_CONFIG.indexTypes,
  topK: 5,
  rerankOn: 'parent',
  rerankPool: 40,
  prefetchLimit: 80,
};

export default function ExperimentForm({
  open,
  onOpenChange,
  fixedValues = {},
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fixedValues?: Partial<ExperimentValues>;
}) {
  const { data: bases } = useKnowledgeBases();
  const { data: datasets } = useDatasets();
  const { data: embeddingModels } = useModels(1, 'bi-encoder', 100);
  const { data: rerankModels } = useModels(1, 'cross-encoder', 100);
  const { data: chatModels } = useModels(1, 'decoder', 100);
  const create = useCreateExperiment();
  const values = { ...VALUES, ...fixedValues };
  const fixed = (field: keyof ExperimentValues) => field in fixedValues;
  const [knowledgeId, setKnowledgeId] = useState(values.knowledgeId);
  const [reranker, setReranker] = useState<KnowledgeBaseConfig['reranker']>(null);
  const [queryExpansion, setQueryExpansion] =
    useState<KnowledgeBaseConfig['queryExpansion']>(null);
  const base = bases?.find((kb) => kb.id === knowledgeId);
  const canRerank = knowledgeId ? !!base?.config.reranker : !!reranker;

  const ready = datasets?.items.filter((d) => d.status === 'ready') ?? [];

  /** Disabled controls are left out of FormData, so fixed values fill the gaps. */
  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const num = (field: keyof ExperimentValues) =>
      Number(form.get(field) ?? values[field as keyof ExperimentValues]);

    const kbConfig: KnowledgeBaseConfig | null = knowledgeId
      ? null
      : {
          chunkingMethod: (form.get('chunkingMethod') ?? values.chunkingMethod) as ChunkingMethod,
          chunkingModelId: String(form.get('chunkingModelId') ?? values.chunkingModelId) || null,
          maxChunkSize: num('maxChunkSize'),
          minChunkSize: num('minChunkSize'),
          indexTypes: fixed('indexTypes')
            ? values.indexTypes
            : (form.getAll('indexTypes') as string[]).map((v) =>
                v === 'bm25' ? { type: 'bm25' as const } : { type: 'vector' as const, modelId: v },
              ),
          reranker,
          queryExpansion,
        };
    const rerankOn = canRerank
      ? ((form.get('rerankOn') ?? values.rerankOn) as ExperimentValues['rerankOn'])
      : '';

    create
      .mutateAsync({
        datasetId: String(form.get('datasetId') ?? values.datasetId),
        knowledgeId: knowledgeId || null,
        kbConfig,
        retrievalConfig: {
          indexTypes: kbConfig?.indexTypes ?? base?.config.indexTypes ?? values.indexTypes,
          topK: num('topK'),
          rerankOn: rerankOn || null,
          rerankPool: num('rerankPool'),
          prefetchLimit: num('prefetchLimit'),
        },
        metrics: form.getAll('metrics') as Metric[],
      })
      .then(() => onOpenChange(false));
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 flex max-h-[85vh] w-[90vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
          <div className="border-b border-slate-100 px-6 py-5">
            <Dialog.Title className="text-base font-semibold">New experiment</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-slate-500">
              One configuration, answered against every pair in a dataset and scored in the
              background.
            </Dialog.Description>
          </div>

          <form onSubmit={submit} className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="min-h-0 flex-1 space-y-7 overflow-y-auto px-6 py-5">
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Subject
                </h3>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Dataset">
                    <select
                      name="datasetId"
                      className={lockable}
                      defaultValue={values.datasetId}
                      disabled={fixed('datasetId')}
                      required
                    >
                      <option value="">Select a dataset</option>
                      {ready.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Knowledge base" hint="none — index a new one">
                    <select
                      name="knowledgeId"
                      className={lockable}
                      value={knowledgeId}
                      disabled={fixed('knowledgeId')}
                      onChange={(e) => setKnowledgeId(e.target.value)}
                    >
                      <option value="">New base</option>
                      {bases?.map((kb) => (
                        <option key={kb.id} value={kb.id}>
                          {kb.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
              </section>

              {/* Index time — only when the run builds its own base; an existing one is already indexed. */}
              {!knowledgeId && (
                <section className="space-y-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Indexing
                  </h3>

                  <Field
                    label="Chunking method"
                    hint="how documents are split into parent chunks"
                  >
                    <select
                      name="chunkingMethod"
                      className={lockable}
                      defaultValue={values.chunkingMethod}
                      disabled={fixed('chunkingMethod')}
                    >
                      {CHUNKING_METHODS.map((m) => (
                        <option key={m}>{m}</option>
                      ))}
                    </select>
                  </Field>

                  <Field label="Chunking model" hint="needed for semantic chunking">
                    <select
                      name="chunkingModelId"
                      className={lockable}
                      defaultValue={values.chunkingModelId}
                      disabled={fixed('chunkingModelId')}
                    >
                      <option value="">None</option>
                      {embeddingModels?.items.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  </Field>

                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Parent chunk size" hint="retrieved for context">
                      <Num
                        name="maxChunkSize"
                        suffix="tokens"
                        min={1}
                        max={8192}
                        value={values.maxChunkSize}
                        disabled={fixed('maxChunkSize')}
                      />
                    </Field>
                    <Field label="Child chunk size" hint="embedded and searched">
                      <Num
                        name="minChunkSize"
                        suffix="tokens"
                        min={1}
                        max={8192}
                        value={values.minChunkSize}
                        disabled={fixed('minChunkSize')}
                      />
                    </Field>
                  </div>

                  <div className="space-y-2">
                    <span className="block text-sm font-medium text-slate-700">
                      Index types
                    </span>
                    {[
                      { value: 'bm25', label: 'BM25' },
                      ...(embeddingModels?.items.map((m) => ({ value: m.id, label: m.name })) ?? []),
                    ].map(({ value, label }) => (
                      <label key={value} className="flex items-center gap-2.5">
                        <input
                          type="checkbox"
                          name="indexTypes"
                          value={value}
                          defaultChecked={values.indexTypes.some((t) =>
                            t.type === 'bm25' ? value === 'bm25' : t.modelId === value,
                          )}
                          disabled={fixed('indexTypes')}
                          className="accent-indigo-600"
                        />
                        <span className="text-sm text-slate-600">{label}</span>
                      </label>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Reranker" hint="reorders results by relevance">
                      <select
                        className={lockable}
                        value={reranker?.type ?? ''}
                        onChange={(e) =>
                          setReranker(
                            e.target.value === 'cross-encoder' ||
                              e.target.value === 'late-interaction'
                              ? { type: e.target.value, modelId: '' }
                              : null,
                          )
                        }
                      >
                        <option value="">None</option>
                        <option value="cross-encoder">Cross-encoder</option>
                        <option value="late-interaction">Late interaction</option>
                      </select>
                    </Field>
                    <Field label="Reranker model">
                      <select
                        className={lockable}
                        value={reranker?.modelId ?? ''}
                        disabled={!reranker}
                        required={!!reranker}
                        onChange={(e) =>
                          reranker && setReranker({ ...reranker, modelId: e.target.value })
                        }
                      >
                        <option value="">Select a model</option>
                        {(reranker?.type === 'late-interaction'
                          ? embeddingModels?.items
                          : rerankModels?.items
                        )?.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name}
                          </option>
                        ))}
                      </select>
                    </Field>
                  </div>

                  <Field label="Query expansion" hint="rewrites the query before searching">
                    <select
                      className={lockable}
                      value={queryExpansion?.modelId ?? ''}
                      onChange={(e) =>
                        setQueryExpansion(e.target.value ? { modelId: e.target.value } : null)
                      }
                    >
                      <option value="">Off</option>
                      {chatModels?.items.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                  </Field>
                </section>
              )}

              {/* Query time — how that base is searched on every question. */}
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Retrieval
                </h3>

                <div className="grid grid-cols-2 gap-4">
                  <Field label="Top K" hint="parent chunks kept">
                    <Num
                      name="topK"
                      suffix="chunks"
                      min={1}
                      max={100}
                      value={values.topK}
                      disabled={fixed('topK')}
                    />
                  </Field>
                  <Field
                    label="Rerank on"
                    hint={canRerank ? 'cross-encoder rescoring' : 'base has no reranker'}
                  >
                    <select
                      name="rerankOn"
                      className={lockable}
                      defaultValue={values.rerankOn}
                      disabled={fixed('rerankOn') || !canRerank}
                    >
                      <option value="">off</option>
                      <option value="parent">parent chunk</option>
                      <option value="child">child chunk</option>
                    </select>
                  </Field>
                  <Field label="Rerank pool" hint="scored before the cut">
                    <Num
                      name="rerankPool"
                      suffix="chunks"
                      min={1}
                      max={500}
                      value={values.rerankPool}
                      disabled={fixed('rerankPool')}
                    />
                  </Field>
                  <Field label="Prefetch limit" hint="candidates per index before fusion">
                    <Num
                      name="prefetchLimit"
                      suffix="chunks"
                      min={1}
                      max={1000}
                      value={values.prefetchLimit}
                      disabled={fixed('prefetchLimit')}
                    />
                  </Field>
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Metrics
                </h3>

                <div className="space-y-2">
                  {(
                    [
                      ['context_precision', 'Context precision', 'retrieved chunks that are relevant'],
                      ['context_recall', 'Context recall', 'relevant chunks that were retrieved'],
                      ['hit_rate', 'Hit rate', 'the source chunk appears in the top-k'],
                      ['mrr', 'MRR', 'how high the source chunk ranks'],
                    ] satisfies [Metric, string, string][]
                  ).map(([metric, name, why]) => (
                    <label key={metric} className="flex items-start gap-2.5">
                      <input
                        type="checkbox"
                        name="metrics"
                        value={metric}
                        defaultChecked
                        className="mt-0.5 accent-indigo-600"
                      />
                      <span className="min-w-0">
                        <span className="block text-sm text-slate-600">{name}</span>
                        <span className="block text-xs text-slate-400">{why}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </section>
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-100 px-6 py-4">
              {create.isError && (
                <p className="mr-auto text-xs text-red-600">{errorMessage(create.error)}</p>
              )}
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="submit"
                disabled={create.isPending}
                className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
              >
                <Play size={16} /> {create.isPending ? 'Starting…' : 'Run'}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
