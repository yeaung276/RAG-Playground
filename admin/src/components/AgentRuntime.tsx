import { useKnowledgeBases } from '../api/knowledge';
import { useModels } from '../api/models';
import type { Agent } from '../types/agent';

interface Props {
  agent: Agent;
  onEdit: (patch: Partial<Agent>) => void;
}

export default function AgentRuntime({ agent, onEdit }: Props) {
  const { data: models } = useModels(1, 'decoder', 100);
  const { data: bases } = useKnowledgeBases();

  return (
    <div className="max-w-3xl space-y-6">
      <div className="divide-y divide-slate-100">
        <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0 sm:pt-1.5">
            <p className="text-sm font-medium text-slate-700">Model</p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              Chat models registered on the Models page.
            </p>
          </div>
          <select
            value={agent.modelId ?? ''}
            onChange={(e) => onEdit({ modelId: e.target.value || null })}
            className="w-64 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">None</option>
            {models?.items.map((m) => (
              <option key={m.id} value={m.id}>
                {m.provider} · {m.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0 sm:pt-1.5">
            <p className="text-sm font-medium text-slate-700">Temperature</p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              0 is deterministic, 100 is the most varied.
            </p>
          </div>
          <input
            type="number"
            min={0}
            max={100}
            value={agent.temperature}
            onChange={(e) =>
              onEdit({ temperature: Math.min(100, Math.max(0, Number(e.target.value) || 0)) })
            }
            className="w-64 shrink-0 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0 sm:pt-1.5">
            <p className="text-sm font-medium text-slate-700">Max steps</p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              How many tool-call rounds before the agent must answer.
            </p>
          </div>
          <input
            type="number"
            min={1}
            value={agent.maxStep}
            onChange={(e) => onEdit({ maxStep: Math.max(1, Number(e.target.value) || 1) })}
            className="w-64 shrink-0 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0 sm:pt-1.5">
            <p className="text-sm font-medium text-slate-700">Knowledge</p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              Attach knowledge to give this agent retrieval over its documents.
            </p>
          </div>
          <select
            value={agent.knowledgeId ?? ''}
            onChange={(e) => onEdit({ knowledgeId: e.target.value || null })}
            className="w-64 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">None</option>
            {bases?.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-end justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              System prompt
            </p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              Prepended to every turn. Handoff descriptions are appended automatically as tool
              descriptions — no need to restate them here.
            </p>
          </div>
          <span className="shrink-0 text-[11px] text-slate-400">
            {agent.instruction.length} chars
          </span>
        </div>
        <textarea
          value={agent.instruction}
          onChange={(e) => onEdit({ instruction: e.target.value })}
          rows={14}
          spellCheck={false}
          placeholder="You are a helpful assistant for…"
          className="w-full resize-y rounded-lg border border-slate-300 px-3 py-2.5 font-mono text-[13px] leading-relaxed outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
      </div>
    </div>
  );
}
