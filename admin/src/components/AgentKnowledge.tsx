import { useKnowledgeBases } from '../api/knowledge';
import { useModels } from '../api/models';
import type { Agent, KnowledgeConfig } from '../types/agent';

type IndexSpec = KnowledgeConfig['indexTypes'][number];

const indexKey = (t: IndexSpec) => (t.type === 'bm25' ? 'bm25' : t.modelId);

interface Props {
  agent: Agent;
  onEdit: (patch: Partial<Agent>) => void;
}

// Blank numbers are sent as null so the server's own defaults apply.
const EMPTY: KnowledgeConfig = {
  indexTypes: [],
  topK: null,
  rerankOn: null,
  rerankPool: null,
  prefetchLimit: null,
  hyde: false,
};

export default function AgentKnowledge({ agent, onEdit }: Props) {
  const { data: bases } = useKnowledgeBases();
  const { data: embeddingModels } = useModels(1, 'bi-encoder', 100);
  const base = bases?.find((kb) => kb.id === agent.knowledgeId);
  const config = agent.knowledgeConfig ?? EMPTY;

  function set(patch: Partial<KnowledgeConfig>) {
    onEdit({ knowledgeConfig: { ...config, ...patch } });
  }

  function toggleIndex(index: IndexSpec, on: boolean) {
    set({
      indexTypes: on
        ? [...config.indexTypes, index]
        : config.indexTypes.filter((t) => indexKey(t) !== indexKey(index)),
    });
  }

  function indexLabel(index: IndexSpec) {
    if (index.type === 'bm25') return 'BM25';
    return embeddingModels?.items.find((m) => m.id === index.modelId)?.name ?? index.modelId;
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="divide-y divide-slate-100">
        <Row
          label="Knowledge"
          hint="Attach knowledge to give this agent retrieval over its documents."
        >
          <select
            value={agent.knowledgeId ?? ''}
            onChange={(e) =>
              onEdit({
                knowledgeId: e.target.value || null,
                // Index types belong to the base, so the config cannot survive a swap.
                knowledgeConfig: null,
              })
            }
            className="w-64 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">None</option>
            {bases?.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </Row>
      </div>

      {agent.knowledgeId && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Retrieval config
          </p>
          <p className="mt-0.5 text-[11px] text-slate-400">
            How the attached knowledge is searched on every turn. Leave a number blank to use the
            server default.
          </p>

          <div className="mt-1 divide-y divide-slate-100">
            <Row
              label="Index types"
              hint="Which indexes to search. More than one is fused by rank. Only the indexes this base was built with are offered."
            >
              <div className="flex w-64 shrink-0 flex-col gap-1.5">
                {base?.config.indexTypes.length ? (
                  base.config.indexTypes.map((t) => (
                    <label key={indexKey(t)} className="flex items-center gap-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={config.indexTypes.some((c) => indexKey(c) === indexKey(t))}
                        onChange={(e) => toggleIndex(t, e.target.checked)}
                        className="accent-indigo-600"
                      />
                      {indexLabel(t)}
                    </label>
                  ))
                ) : (
                  <span className="text-[11px] text-slate-400">
                    This base has no indexes configured.
                  </span>
                )}
              </div>
            </Row>

            <Row
              label="HyDE"
              hint="Search with a hypothetical answer generated from the query. Needs a HyDE model on this base."
            >
              <label className="flex w-64 shrink-0 items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={config.hyde}
                  disabled={!base?.config.hyde}
                  onChange={(e) => set({ hyde: e.target.checked })}
                  className="accent-indigo-600"
                />
                Enabled
              </label>
            </Row>

            <Row label="Top K" hint="How many parent chunks are handed to the model.">
              <NumberInput
                value={config.topK}
                placeholder="Server default"
                onChange={(v) => set({ topK: v })}
              />
            </Row>

            <Row
              label="Rerank on"
              hint="Rescore hits with a cross-encoder before cutting to Top K — on the parent chunk or on the child that matched. Off skips reranking."
            >
              <select
                value={config.rerankOn ?? ''}
                onChange={(e) =>
                  set({ rerankOn: (e.target.value || null) as KnowledgeConfig['rerankOn'] })
                }
                className="w-64 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">Off</option>
                <option value="parent">Parent chunk</option>
                <option value="child">Child chunk</option>
              </select>
            </Row>

            <Row
              label="Rerank pool"
              hint="How many hits the reranker scores before the cut. Defaults to Top K."
            >
              <NumberInput
                value={config.rerankPool}
                placeholder="Top K"
                onChange={(v) => set({ rerankPool: v })}
              />
            </Row>

            <Row
              label="Prefetch limit"
              hint="How many candidates each index contributes before fusion. Defaults to twice the rerank pool."
            >
              <NumberInput
                value={config.prefetchLimit}
                placeholder="Twice the rerank pool"
                onChange={(v) => set({ prefetchLimit: v })}
              />
            </Row>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  hint,
  children,
}: {
  label: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
      <div className="min-w-0 sm:pt-1.5">
        <p className="text-sm font-medium text-slate-700">{label}</p>
        <p className="mt-0.5 text-[11px] text-slate-400">{hint}</p>
      </div>
      {children}
    </div>
  );
}

function NumberInput({
  value,
  placeholder,
  onChange,
}: {
  value: number | null;
  placeholder: string;
  onChange: (value: number | null) => void;
}) {
  return (
    <input
      type="number"
      min={1}
      value={value ?? ''}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value === '' ? null : Math.max(1, Number(e.target.value)))}
      className="w-64 shrink-0 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
    />
  );
}
