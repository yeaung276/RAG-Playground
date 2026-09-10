import type { Agent } from '../types/agent';

interface Props {
  agent: Agent;
  onEdit: (patch: Partial<Agent>) => void;
}

export default function AgentGeneral({ agent, onEdit }: Props) {
  return (
    <div className="max-w-3xl space-y-6">
      <div className="divide-y divide-slate-100">
        <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0 sm:pt-1.5">
            <p className="text-sm font-medium text-slate-700">Name</p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              Shown in the roster and used as the handoff target name.
            </p>
          </div>
          <input
            value={agent.name}
            onChange={(e) => onEdit({ name: e.target.value })}
            className={`w-64 shrink-0 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-1 ${
              agent.name.trim()
                ? 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500'
                : 'border-red-400 focus:border-red-500 focus:ring-red-500'
            }`}
          />
        </div>

        <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <div className="min-w-0 sm:pt-1.5">
            <p className="text-sm font-medium text-slate-700">Knowledge base</p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              Attach a base to give this agent retrieval over its documents.
            </p>
          </div>
          <select
            value={agent.kbId}
            onChange={(e) => onEdit({ kbId: e.target.value })}
            className="w-64 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">None</option>
            <option value="kb_treasury">Thai Treasury regulations</option>
            <option value="kb_coins">Commemorative coin catalogue</option>
            <option value="kb_land">Land appraisal handbook</option>
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
            {agent.prompt.length} chars
          </span>
        </div>
        <textarea
          value={agent.prompt}
          onChange={(e) => onEdit({ prompt: e.target.value })}
          rows={14}
          spellCheck={false}
          placeholder="You are a helpful assistant for…"
          className="w-full resize-y rounded-lg border border-slate-300 px-3 py-2.5 font-mono text-[13px] leading-relaxed outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
      </div>
    </div>
  );
}
