import { useEffect, useState } from 'react';
import { Bot, FlaskConical } from 'lucide-react';
import AgentGeneral from '../components/AgentGeneral';
import AgentHandoffs from '../components/AgentHandoffs';
import AgentRuntime from '../components/AgentRuntime';
import AgentTools from '../components/AgentTools';
import AgentTopology from '../components/AgentTopology';
import AgentTrace from '../components/AgentTrace';
import Header from '../components/Header';
import Modal from '../components/Modal';
import NamePromptModal from '../components/NamePromptModal';
import { pushToast } from '../components/Toast';
import {
  useAgent,
  useAgents,
  useCreateAgent,
  useDeleteAgent,
  useSetEntrypoint,
  useUpdateAgent,
  type Agent as ApiAgent,
  type AgentPatch,
} from '../api/agents';
import { errorMessage } from '../api/client';
import { uid, type Agent, type Param, type Tool } from '../types/agent';

// The roster on the left is server state; the tabs on the right edit a draft of
// the selected agent, sent as one PATCH on save.

const TABS = [
  { id: 'general', label: 'General' },
  { id: 'runtime', label: 'Runtime' },
  { id: 'tools', label: 'Tools' },
  { id: 'handoffs', label: 'Handoffs' },
] as const;
type Tab = (typeof TABS)[number]['id'];

function toDraft(a: ApiAgent): Agent {
  return {
    id: a.id,
    name: a.name,
    description: a.description,
    instruction: a.instruction,
    modelId: a.modelId,
    temperature: a.temperature,
    knowledgeId: a.knowledgeId,
    maxStep: a.maxStep,
    isEntrypoint: a.isEntrypoint,
    handoffMode: a.handoff.mode,
    handoffs: a.handoff.targets.map((t) => ({
      id: t.id ?? uid(),
      targetId: t.agentId,
      description: t.description,
    })),
    tools: a.tools.map((t) => ({
      ...t,
      id: t.id ?? uid(),
      method: t.method as Tool['method'],
      headers: t.headers.map((h) => ({ ...h, id: h.id ?? uid() })),
      query: t.query.map((q) => ({ ...q, id: q.id ?? uid() })),
      params: t.params.map((p) => ({ ...p, id: p.id ?? uid(), type: p.type as Param['type'] })),
      authToken: '',
      saved: true,
    })),
  };
}

/** A blank `authToken` means "keep the stored one", so it is left off the wire. */
function toPatch(d: Agent): AgentPatch {
  return {
    description: d.description,
    instruction: d.instruction,
    modelId: d.modelId,
    temperature: d.temperature,
    knowledgeId: d.knowledgeId,
    maxStep: d.maxStep,
    handoff: {
      mode: d.handoffMode,
      targets: d.handoffs.map((h) => ({
        id: h.id,
        agentId: h.targetId,
        description: h.description,
      })),
    },
    tools: d.tools.map(({ hasAuthToken, saved, authToken, ...rest }) => ({
      ...rest,
      ...(authToken ? { authToken } : {}),
    })),
  };
}

export default function Agents() {
  const { data: roster = [], isLoading, error } = useAgents();
  const createAgent = useCreateAgent();
  const deleteAgent = useDeleteAgent();
  const setEntrypoint = useSetEntrypoint();
  const updateAgent = useUpdateAgent();

  const [selectedId, setSelectedId] = useState('');
  const [tab, setTab] = useState<Tab>('general');
  const [naming, setNaming] = useState(false);
  const [testing, setTesting] = useState(false);
  const [draft, setDraft] = useState<Agent | null>(null);

  // The roster carries counts only, so the selected agent is fetched in full.
  const currentId = roster.find((a) => a.id === selectedId)?.id ?? roster[0]?.id ?? '';
  const { data: selected, isLoading: loadingAgent } = useAgent(currentId);

  // Re-seed the draft whenever the selection changes or the row is refetched.
  useEffect(() => {
    setDraft(selected ? toDraft(selected) : null);
  }, [selected?.id, selected?.updatedAt]);

  const agent = draft;
  const others = roster.filter((a) => a.id !== currentId);
  const dirty = !!selected && !!agent && JSON.stringify(agent) !== JSON.stringify(toDraft(selected));

  const activeTab: Tab = tab;

  // Patch the local draft of the selected agent.
  function edit(patch: Partial<Agent>) {
    setDraft((prev) => (prev ? { ...prev, ...patch } : prev));
  }

  function addAgent(name: string) {
    createAgent.mutate(
      { name },
      {
        onSuccess: (created) => setSelectedId(created.id),
        onError: (err) => pushToast(errorMessage(err)),
      },
    );
  }

  function removeAgent(id: string) {
    deleteAgent.mutate(id, {
      onSuccess: () => {
        if (selectedId === id) setSelectedId('');
      },
      onError: (err) => pushToast(errorMessage(err)),
    });
  }

  function promote(id: string) {
    setEntrypoint.mutate(id, {
      onSuccess: (a) => pushToast(`${a.name} is now the entrypoint.`, 'success'),
      onError: (err) => pushToast(errorMessage(err)),
    });
  }

  function save() {
    if (!agent) return;
    if (agent.tools.some((t) => !t.name.trim())) {
      pushToast('Every tool needs a name.');
      return;
    }
    const names = agent.tools.map((t) => t.name.trim());
    if (new Set(names).size !== names.length) {
      pushToast('Tool names must be unique — they are the key the server saves against.');
      return;
    }
    updateAgent.mutate(
      { id: agent.id, patch: toPatch(agent) },
      {
        onSuccess: () => pushToast('Agent saved.', 'success'),
        onError: (err) => pushToast(errorMessage(err)),
      },
    );
  }

  function reset() {
    setDraft(selected ? toDraft(selected) : null);
  }

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      <Header>
        <Bot size={18} className="text-indigo-600" />
        <h1 className="truncate text-base font-semibold">Agents</h1>
        <button
          onClick={() => setTesting(true)}
          disabled={!roster.length}
          className="ml-2 flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <FlaskConical size={15} />
          Test
        </button>
      </Header>

      <div className="flex min-h-0 flex-1 gap-5 px-6 py-5">
        <AgentTopology
          agents={roster}
          selectedId={currentId}
          onSelect={setSelectedId}
          onAdd={() => setNaming(true)}
          onRemove={removeAgent}
          onSetEntrypoint={promote}
        />

        <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
          {isLoading || loadingAgent || error || !agent ? (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-400">
              {isLoading || loadingAgent
                ? 'Loading agents…'
                : error
                  ? errorMessage(error)
                  : 'No agents. Add one to get started.'}
            </div>
          ) : (
            <>
              <div className="flex gap-1 border-b border-slate-200 px-6 pt-1">
                {TABS.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={`-mb-px border-b-2 px-3 py-2.5 text-sm font-medium transition ${
                      activeTab === t.id
                        ? 'border-indigo-600 text-indigo-700'
                        : 'border-transparent text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              <div className="min-h-0 flex-1 overflow-auto px-6 py-5">
                {activeTab === 'general' && <AgentGeneral agent={agent} onEdit={edit} />}
                {activeTab === 'runtime' && <AgentRuntime agent={agent} onEdit={edit} />}
                {activeTab === 'tools' && <AgentTools agent={agent} onEdit={edit} />}
                {activeTab === 'handoffs' && (
                  <AgentHandoffs agent={agent} others={others} onEdit={edit} />
                )}
              </div>

              <div className="flex items-center justify-between gap-4 border-t border-slate-200 bg-slate-50 px-6 py-3">
                <p className="text-xs text-slate-500">
                  {dirty ? 'Unsaved changes.' : 'No unsaved changes.'}
                </p>
                <div className="flex shrink-0 gap-2">
                  <button
                    onClick={reset}
                    disabled={!dirty}
                    className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Reset
                  </button>
                  <button
                    onClick={save}
                    disabled={!dirty || updateAgent.isPending}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {updateAgent.isPending ? 'Saving…' : 'Save changes'}
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      </div>

      <Modal
        open={testing}
        onOpenChange={setTesting}
        title="Test run"
        subtitle={`${roster.find((a) => a.isEntrypoint)?.name ?? 'No entrypoint'} — nothing here is saved`}
        size="lg"
      >
        {testing && <AgentTrace />}
      </Modal>

      <NamePromptModal
        open={naming}
        onOpenChange={setNaming}
        title="Add agent"
        label="Agent name"
        placeholder="e.g. Refunds Agent"
        submitLabel="Add agent"
        onSubmit={addAgent}
      />
    </div>
  );
}
