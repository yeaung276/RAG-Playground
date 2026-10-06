import { useEffect, useRef, useState, type ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { useForm, useSelector } from '@tanstack/react-form';
import { Plus, Trash2, X } from 'lucide-react';
import { z } from 'zod';
import {
  CHUNKING_METHODS,
  DEFAULT_CONFIG,
  knowledgeBaseConfigSchema,
  type ChunkingMethod,
  type KnowledgeBaseConfig,
} from '../api/config';
import { useModels } from '../api/models';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (name: string, config: KnowledgeBaseConfig) => Promise<void>;
}

const formSchema = z
  .object({ name: z.string().trim().min(1, 'Enter a name') })
  .and(knowledgeBaseConfigSchema);

export default function NewKbModal({ open, onOpenChange, onSubmit }: Props) {
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);
  const { data: embeddingModels } = useModels(1, 'bi-encoder', 100);
  const { data: rerankModels } = useModels(1, 'cross-encoder', 100);
  const { data: chatModels } = useModels(1, 'decoder', 100);

  const form = useForm({
    defaultValues: { name: '', ...DEFAULT_CONFIG },
    validators: { onChange: formSchema },
    onSubmit: async ({ value: { name, ...config } }) => {
      setError(null);
      try {
        await onSubmit(name.trim(), config);
        onOpenChange(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Something went wrong');
      }
    },
  });

  useEffect(() => {
    if (open) {
      form.reset();
      setError(null);
    }
  }, [open, form]);

  const chunkingMethod = useSelector(form.store, (s) => s.values.chunkingMethod);
  const indexTypes = useSelector(form.store, (s) => s.values.indexTypes);
  const hasBm25 = indexTypes.some((t) => t.type === 'bm25');
  const usedModelIds = indexTypes.flatMap((t) => (t.type === 'vector' ? [t.modelId] : []));

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 flex max-h-[85vh] w-[90vw] max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col rounded-xl bg-white shadow-xl focus:outline-none"
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            nameRef.current?.focus();
          }}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              form.handleSubmit();
            }}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
              <Dialog.Title className="text-base font-semibold text-slate-900">
                New knowledge
              </Dialog.Title>
              <Dialog.Close
                type="button"
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                <X size={18} />
              </Dialog.Close>
            </div>

            <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 py-5">
              <Section title="General">
                <form.Field name="name">
                  {(field) => (
                    <Row title="Name" error={touchedError(field.state.meta)}>
                      <input
                        ref={nameRef}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        placeholder="e.g. Coin regulations"
                        className={`${CONTROL} w-52`}
                      />
                    </Row>
                  )}
                </form.Field>
              </Section>

              <Section title="Chunking">
                <form.Field name="chunkingMethod">
                  {(field) => (
                    <Row title="Method" hint="How documents are split into parent chunks.">
                      <select
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.value as ChunkingMethod)}
                        onBlur={field.handleBlur}
                        className={CONTROL}
                      >
                        {CHUNKING_METHODS.map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </Row>
                  )}
                </form.Field>

                {chunkingMethod === 'semantic' && (
                  <form.Field name="chunkingModelId">
                    {(field) => (
                      <Row
                        title="Embedding model"
                        hint="Finds topic breaks between sentences."
                        error={touchedError(field.state.meta)}
                      >
                        <select
                          value={field.state.value ?? ''}
                          onChange={(e) => field.handleChange(e.target.value || null)}
                          onBlur={field.handleBlur}
                          className={CONTROL}
                        >
                          <option value="">Select a model</option>
                          {embeddingModels?.items.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.name}
                            </option>
                          ))}
                        </select>
                      </Row>
                    )}
                  </form.Field>
                )}

                <form.Field name="maxChunkSize">
                  {(field) => (
                    <Row
                      title="Parent chunk size"
                      hint="Tokens kept for context."
                      error={firstError(field.state.meta.errors)}
                    >
                      <input
                        type="number"
                        min={1}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.valueAsNumber)}
                        onBlur={field.handleBlur}
                        className={`${CONTROL} w-24`}
                      />
                    </Row>
                  )}
                </form.Field>

                <form.Field name="minChunkSize">
                  {(field) => (
                    <Row
                      title="Child chunk size"
                      hint="Tokens embedded for search."
                      error={firstError(field.state.meta.errors)}
                    >
                      <input
                        type="number"
                        min={1}
                        value={field.state.value}
                        onChange={(e) => field.handleChange(e.target.valueAsNumber)}
                        onBlur={field.handleBlur}
                        className={`${CONTROL} w-24`}
                      />
                    </Row>
                  )}
                </form.Field>
              </Section>

              <form.Field name="indexTypes" mode="array">
                {(arrayField) => (
                  <Section title="Indexing" error={firstError(arrayField.state.meta.errors)}>
                    {arrayField.state.value.map((index, i) => (
                      <form.Field key={i} name={`indexTypes[${i}]`}>
                        {(field) => (
                          <Row
                            title={index.type === 'bm25' ? 'Sparse' : 'Dense'}
                            hint={index.type === 'bm25' ? 'Keyword match.' : 'Meaning match.'}
                          >
                            <select
                              value={index.type === 'bm25' ? 'bm25' : index.modelId}
                              onChange={(e) =>
                                field.handleChange(
                                  e.target.value === 'bm25'
                                    ? { type: 'bm25' }
                                    : { type: 'vector', modelId: e.target.value },
                                )
                              }
                              onBlur={field.handleBlur}
                              className={CONTROL}
                            >
                              <option value="">Select an index</option>
                              <optgroup label="Sparse">
                                <option value="bm25" disabled={hasBm25 && index.type !== 'bm25'}>
                                  BM25
                                </option>
                              </optgroup>
                              <optgroup label="Dense">
                                {embeddingModels?.items
                                  .filter(
                                    (m) =>
                                      (index.type === 'vector' && m.id === index.modelId) ||
                                      !usedModelIds.includes(m.id),
                                  )
                                  .map((m) => (
                                    <option key={m.id} value={m.id}>
                                      {m.name}
                                    </option>
                                  ))}
                              </optgroup>
                            </select>
                            <button
                              type="button"
                              aria-label="Remove index"
                              onClick={() => arrayField.removeValue(i)}
                              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-red-600"
                            >
                              <Trash2 size={15} />
                            </button>
                          </Row>
                        )}
                      </form.Field>
                    ))}
                    <div className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() => arrayField.pushValue({ type: 'vector', modelId: '' })}
                        className="flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700"
                      >
                        <Plus size={15} />
                        Add index
                      </button>
                    </div>
                  </Section>
                )}
              </form.Field>

              <Section title="Retrieval">
                <form.Field name="reranker">
                  {(field) => {
                    const reranker = field.state.value;
                    const models =
                      reranker?.type === 'late-interaction'
                        ? embeddingModels?.items
                        : rerankModels?.items;
                    return (
                      <Row title="Reranker" hint="Reorders results by relevance.">
                        <select
                          value={reranker?.type ?? ''}
                          onChange={(e) =>
                            field.handleChange(
                              e.target.value === 'cross-encoder' ||
                                e.target.value === 'late-interaction'
                                ? { type: e.target.value, modelId: '' }
                                : null,
                            )
                          }
                          onBlur={field.handleBlur}
                          className={CONTROL}
                        >
                          <option value="">None</option>
                          <option value="cross-encoder">Cross-encoder</option>
                          <option value="late-interaction">Late interaction</option>
                        </select>
                        <select
                          value={reranker?.modelId ?? ''}
                          disabled={!reranker}
                          onChange={(e) =>
                            reranker && field.handleChange({ ...reranker, modelId: e.target.value })
                          }
                          onBlur={field.handleBlur}
                          className={CONTROL}
                        >
                          <option value="">Select a model</option>
                          {models?.map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.name}
                            </option>
                          ))}
                        </select>
                      </Row>
                    );
                  }}
                </form.Field>

                <form.Field name="queryExpansion">
                  {(field) => (
                    <Row title="Query expansion" hint="Rewrites the query before searching.">
                      <select
                        value={field.state.value?.modelId ?? ''}
                        onChange={(e) =>
                          field.handleChange(e.target.value ? { modelId: e.target.value } : null)
                        }
                        onBlur={field.handleBlur}
                        className={CONTROL}
                      >
                        <option value="">Off</option>
                        {chatModels?.items.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.name}
                          </option>
                        ))}
                      </select>
                    </Row>
                  )}
                </form.Field>
              </Section>
            </div>

            <div className="flex items-center justify-between gap-4 border-t border-slate-200 px-6 py-4">
              <p className="min-w-0 truncate text-sm text-red-600">{error}</p>
              <div className="flex shrink-0 gap-2">
                <Dialog.Close
                  type="button"
                  className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </Dialog.Close>
                <form.Subscribe selector={(s) => [s.canSubmit, s.isSubmitting] as const}>
                  {([canSubmit, isSubmitting]) => (
                    <button
                      type="submit"
                      disabled={!canSubmit || isSubmitting}
                      className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isSubmitting ? 'Creating…' : 'Create'}
                    </button>
                  )}
                </form.Subscribe>
              </div>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const CONTROL =
  'max-w-44 rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400';

function firstError(errors: unknown[]): string | undefined {
  const e = errors.find(Boolean);
  if (!e) return undefined;
  return typeof e === 'string' ? e : (e as { message?: string }).message;
}

function touchedError(meta: { isTouched: boolean; errors: unknown[] }): string | undefined {
  return meta.isTouched ? firstError(meta.errors) : undefined;
}

function Section({
  title,
  error,
  children,
}: {
  title: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-200">
      <header className="flex items-center justify-between gap-4 border-b border-slate-100 px-4 py-2.5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</h3>
        {error && <span className="text-xs text-red-600">{error}</span>}
      </header>
      <div className="divide-y divide-slate-100">{children}</div>
    </section>
  );
}

function Row({
  title,
  hint,
  error,
  children,
}: {
  title: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-800">{title}</p>
        {(error || hint) && (
          <p className={`text-xs ${error ? 'text-red-600' : 'text-slate-500'}`}>{error ?? hint}</p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">{children}</div>
    </div>
  );
}
