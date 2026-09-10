import { Bot, Crown, GitBranch, Network, Plus, Trash2, Users, Wrench } from 'lucide-react';

// Roster + routing panel. Topology is derived from the agent count — never chosen.

type RosterAgent = {
  id: string;
  name: string;
  role: 'manager' | 'subagent';
  tools: { enabled: boolean }[];
  handoffs: { id: string; targetId: string; }[];
};

interface Props {
  agents: RosterAgent[];
  selectedId: string;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onRemove: (id: string) => void;
}

export default function AgentTopology({
  agents,
  selectedId,
  onSelect,
  onAdd,
  onRemove,
}: Props) {
  const swarm = agents.length > 1;
  const manager = agents.find((a) => a.role === 'manager');

  return (
    <aside className="flex w-72 shrink-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            {agents.length} agent{agents.length === 1 ? '' : 's'}
          </span>
          <span
            title={
              swarm
                ? 'Swarm: the manager receives every message and hands off to specialists.'
                : 'Single: one agent answers everything. Add an agent and it becomes a swarm.'
            }
            className="flex shrink-0 items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500"
          >
            {swarm ? (
              <>
                <Users size={10} /> Swarm
              </>
            ) : (
              <>
                <Bot size={10} /> Single
              </>
            )}
          </span>
        </div>
        <button
          onClick={onAdd}
          className="flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50"
        >
          <Plus size={14} /> Add agent
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-1 overflow-auto px-3 py-3">
        {agents.map((a) => (
          <div
            key={a.id}
            onClick={() => onSelect(a.id)}
            className={`group cursor-pointer rounded-lg border px-3 py-2.5 transition ${
              a.id === selectedId
                ? 'border-indigo-300 bg-indigo-50'
                : 'border-transparent hover:bg-slate-50'
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-800">
                {a.name || 'Untitled agent'}
              </span>
              {a.role === 'manager' ? (
                <span
                  title="Manager — the entry point for every message"
                  className="flex shrink-0 items-center gap-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700"
                >
                  <Crown size={10} /> Manager
                </span>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(a.id);
                  }}
                  title="Remove agent"
                  className="shrink-0 rounded p-0.5 text-slate-300 opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              <span
                title={`${a.tools.filter((t) => t.enabled).length} enabled tools`}
                className="flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500"
              >
                <Wrench size={10} /> {a.tools.filter((t) => t.enabled).length}
              </span>
              {a.role === 'manager' && swarm && (
                <span
                  title={`${a.handoffs.length} handoffs`}
                  className="flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500"
                >
                  <GitBranch size={10} /> {a.handoffs.length}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {swarm && manager && (
        <div className="border-t border-slate-200 px-4 py-3">
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
            <Network size={12} /> Routing
          </p>
          {manager.handoffs.map((h) => (
            <p key={h.id} className="truncate font-mono text-[10px] text-slate-500">
              {manager.name} → {agents.find((t) => t.id === h.targetId)?.name ?? '(none)'}
            </p>
          ))}
          {manager.handoffs.length === 0 && (
            <p className="text-[10px] text-slate-400">No handoffs defined.</p>
          )}
        </div>
      )}
    </aside>
  );
}
