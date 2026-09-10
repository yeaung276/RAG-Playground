import { Bot, Crown, GitBranch, Plus, Trash2, Users, Wrench } from 'lucide-react';

// Roster + routing panel. Topology is derived from the agent count — never chosen.

type RosterAgent = {
  id: string;
  name: string;
  isEntrypoint: boolean;
  enabledToolCount: number;
  handoffCount: number;
};

interface Props {
  agents: RosterAgent[];
  selectedId: string;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onRemove: (id: string) => void;
  onSetEntrypoint: (id: string) => void;
}

export default function AgentTopology({
  agents,
  selectedId,
  onSelect,
  onAdd,
  onRemove,
  onSetEntrypoint,
}: Props) {
  const swarm = agents.length > 1;

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
                ? 'Swarm: the entrypoint receives every message and hands off to specialists.'
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
              {a.isEntrypoint ? (
                <span
                  title="Entrypoint — every message starts here"
                  className="flex shrink-0 items-center gap-1 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700"
                >
                  <Crown size={10} /> Entrypoint
                </span>
              ) : (
                <div className="flex shrink-0 gap-0.5 opacity-0 transition group-hover:opacity-100">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSetEntrypoint(a.id);
                    }}
                    title="Make this the entrypoint"
                    className="rounded p-0.5 text-slate-300 transition hover:bg-amber-50 hover:text-amber-600"
                  >
                    <Crown size={13} />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemove(a.id);
                    }}
                    title="Remove agent"
                    className="rounded p-0.5 text-slate-300 transition hover:bg-red-50 hover:text-red-600"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              )}
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              <span
                title={`${a.enabledToolCount} enabled tools`}
                className="flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500"
              >
                <Wrench size={10} /> {a.enabledToolCount}
              </span>
              {a.handoffCount > 0 && (
                <span
                  title={`${a.handoffCount} handoffs`}
                  className="flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500"
                >
                  <GitBranch size={10} /> {a.handoffCount}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

    </aside>
  );
}
