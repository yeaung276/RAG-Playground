import { CornerDownRight, Plus, Trash2 } from 'lucide-react';
import { uid, type Agent, type HandoffMode } from '../types/agent';

// Any agent can route to any other, not just the entrypoint.

const MODES: { id: HandoffMode; label: string; hint: string }[] = [
  { id: 'none', label: 'No handoff', hint: 'This agent answers everything itself.' },
  { id: 'auto', label: 'Auto', hint: 'Every other agent is a target, using its own description.' },
  { id: 'manual', label: 'Manual', hint: 'Only the targets listed below.' },
];

interface Props {
  agent: Agent;
  /** Candidate targets — the roster minus this agent. */
  others: { id: string; name: string }[];
  onEdit: (patch: Partial<Agent>) => void;
}

export default function AgentHandoffs({ agent, others, onEdit }: Props) {
  const usedTargets = new Set(agent.handoffs.map((h) => h.targetId));

  return (
    <div className="max-w-3xl space-y-3">
      <div className="rounded-xl border border-slate-200 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Mode</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {MODES.map((m) => (
            <button
              key={m.id}
              onClick={() => onEdit({ handoffMode: m.id })}
              title={m.hint}
              className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
                agent.handoffMode === m.id
                  ? 'border-indigo-300 bg-indigo-50 text-indigo-700'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] text-slate-400">
          {MODES.find((m) => m.id === agent.handoffMode)?.hint}
        </p>
      </div>

      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Targets</p>
          <p className="mt-0.5 text-[11px] text-slate-400">
            Each handoff becomes a tool this agent can call. The description tells the model when
            to transfer — write it as a routing rule.
          </p>
        </div>
        <button
          onClick={() =>
            onEdit({
              handoffs: [
                ...agent.handoffs,
                {
                  id: uid(),
                  targetId: others.find((o) => !usedTargets.has(o.id))?.id ?? '',
                  description: '',
                },
              ],
            })
          }
          disabled={agent.handoffMode !== 'manual' || others.every((o) => usedTargets.has(o.id))}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus size={15} /> Add handoff
        </button>
      </div>

      {agent.handoffMode !== 'manual' && (
        <p className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400">
          {agent.handoffMode === 'auto'
            ? 'Auto mode: every other agent is reachable. Targets below are ignored.'
            : 'Handoff is off. Switch to Auto or Manual to route to other agents.'}
        </p>
      )}

      {agent.handoffMode === 'manual' && agent.handoffs.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400">
          {others.length === 0
            ? 'Add a second agent to the swarm to define handoffs.'
            : 'No handoffs. This agent answers everything it receives itself.'}
        </p>
      )}

      {agent.handoffMode === 'manual' && agent.handoffs.map((h) => (
        <div key={h.id} className="rounded-xl border border-slate-200 p-4">
          <div className="flex items-center gap-2">
            <CornerDownRight size={15} className="shrink-0 text-slate-400" />
            <span className="shrink-0 text-xs font-medium text-slate-500">Hand off to</span>
            <select
              value={h.targetId}
              onChange={(e) =>
                onEdit({
                  handoffs: agent.handoffs.map((x) =>
                    x.id === h.id ? { ...x, targetId: e.target.value } : x,
                  ),
                })
              }
              className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            >
              <option value="">Select an agent…</option>
              {others.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
            <button
              onClick={() =>
                onEdit({ handoffs: agent.handoffs.filter((x) => x.id !== h.id) })
              }
              title="Remove handoff"
              className="shrink-0 rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
            >
              <Trash2 size={15} />
            </button>
          </div>
          <label className="mt-3 block">
            <span className="text-xs font-medium text-slate-500">Handoff description</span>
            <textarea
              value={h.description}
              onChange={(e) =>
                onEdit({
                  handoffs: agent.handoffs.map((x) =>
                    x.id === h.id ? { ...x, description: e.target.value } : x,
                  ),
                })
              }
              rows={2}
              placeholder="Transfer when the customer asks about…"
              className="mt-1 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </label>
        </div>
      ))}
    </div>
  );
}
