import { CornerDownRight, Plus, Trash2 } from 'lucide-react';
import { uid, type Agent } from '../types/agent';

// Only the manager routes, so this is rendered for the manager alone.

interface Props {
  agent: Agent;
  others: Agent[];
  onEdit: (patch: Partial<Agent>) => void;
}

export default function AgentHandoffs({ agent, others, onEdit }: Props) {
  const usedTargets = new Set(agent.handoffs.map((h) => h.targetId));

  return (
    <div className="max-w-3xl space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Handoffs</p>
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
          disabled={others.every((o) => usedTargets.has(o.id))}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus size={15} /> Add handoff
        </button>
      </div>

      {agent.handoffs.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400">
          {others.length === 0
            ? 'Add a second agent to the swarm to define handoffs.'
            : 'No handoffs. This agent answers everything it receives itself.'}
        </p>
      )}

      {agent.handoffs.map((h) => (
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
