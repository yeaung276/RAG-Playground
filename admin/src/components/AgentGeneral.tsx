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
              Fixed at creation. Delete and re-add the agent to change it.
            </p>
          </div>
          <input
            value={agent.name}
            readOnly
            disabled
            className="w-64 shrink-0 cursor-not-allowed rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500"
          />
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-end justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Description
            </p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              What this agent handles. Other agents read it when deciding whether to hand off.
            </p>
          </div>
          <span className="shrink-0 text-[11px] text-slate-400">
            {agent.description.length} chars
          </span>
        </div>
        <textarea
          value={agent.description}
          onChange={(e) => onEdit({ description: e.target.value })}
          rows={6}
          placeholder="Handles refunds, billing disputes and invoice reissues."
          className="w-full resize-y rounded-lg border border-slate-300 px-3 py-2.5 text-[13px] leading-relaxed outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
      </div>
    </div>
  );
}
