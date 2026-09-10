import { useState } from 'react';
import { Bot } from 'lucide-react';
import AgentGeneral from '../components/AgentGeneral';
import AgentHandoffs from '../components/AgentHandoffs';
import AgentTools from '../components/AgentTools';
import AgentTopology from '../components/AgentTopology';
import Header from '../components/Header';
import NamePromptModal from '../components/NamePromptModal';
import { pushToast } from '../components/Toast';
import { uid, type Agent } from '../types/agent';

// Agent management screen. Everything is local state — nothing hits the backend.

const TABS = [
  { id: 'general', label: 'General' },
  { id: 'tools', label: 'Tools' },
  { id: 'handoffs', label: 'Handoffs' },
] as const;
type Tab = (typeof TABS)[number]['id'];

const SEED: Agent[] = [
  {
    id: 'ag_triage',
    name: 'Triage Manager',
    role: 'manager',
    description: 'Front door. Classifies the request and routes to a specialist.',
    temperature: 0.2,
    maxTokens: 1024,
    prompt:
      'You are the triage manager for the Treasury help desk. Decide which specialist should handle the message and hand off immediately. Reply in the language the customer used.',
    kbId: '',
    handoffs: [
      {
        id: uid(),
        targetId: 'ag_land',
        description: 'Land appraisal prices, title deeds, property valuation.',
      },
      {
        id: uid(),
        targetId: 'ag_coin',
        description: 'Commemorative coin orders, exchange counters, catalogue lookups.',
      },
    ],
    tools: [],
  },
  {
    id: 'ag_land',
    name: 'Land Appraisal Agent',
    role: 'subagent',
    description: 'Answers appraisal-price questions and looks up deeds.',
    temperature: 0.1,
    maxTokens: 2048,
    prompt:
      'You are a land appraisal specialist. Use lookup_appraisal_price for any real figure — never guess a price. Quote the appraisal round with every number.',
    kbId: 'kb_land',
    handoffs: [],
    tools: [
      {
        id: uid(),
        name: 'lookup_appraisal_price',
        description: 'Look up the official appraisal price for a title deed.',
        enabled: true,
        method: 'GET',
        url: 'https://api.treasury.example.com/v1/appraisal/{{deed_no}}',
        headers: [{ id: uid(), key: 'Accept', value: 'application/json' }],
        query: [{ id: uid(), key: 'province', value: '{{province}}' }],
        body: '',
        auth: 'bearer',
        authToken: 'demo-token',
        authHeader: '',
        authUser: '',
        authPass: '',
        timeoutMs: 8000,
        params: [
          {
            id: uid(),
            name: 'deed_no',
            type: 'string',
            required: true,
            description: 'Title deed number, digits only.',
          },
          {
            id: uid(),
            name: 'province',
            type: 'string',
            required: true,
            description: 'Province name in English.',
          },
        ],
      },
    ],
  },
  {
    id: 'ag_coin',
    name: 'Coin Exchange Agent',
    role: 'subagent',
    description: 'Handles coin orders and exchange-counter questions.',
    temperature: 0.3,
    maxTokens: 1536,
    prompt:
      'You are a commemorative coin specialist. Check stock before promising availability, and place an order only after the customer confirms quantity and pickup branch.',
    kbId: 'kb_coins',
    handoffs: [],
    tools: [
      {
        id: uid(),
        name: 'place_coin_order',
        description: 'Reserve coins for pickup. Only call after the customer confirms.',
        enabled: false,
        method: 'POST',
        url: 'https://api.treasury.example.com/v1/coins/orders',
        headers: [{ id: uid(), key: 'Content-Type', value: 'application/json' }],
        query: [],
        body: '{\n  "coinId": "{{coin_id}}",\n  "quantity": {{quantity}}\n}',
        auth: 'header',
        authToken: 'demo-key',
        authHeader: 'X-Api-Key',
        authUser: '',
        authPass: '',
        timeoutMs: 10000,
        params: [
          {
            id: uid(),
            name: 'coin_id',
            type: 'string',
            required: true,
            description: 'Catalogue id of the coin.',
          },
          {
            id: uid(),
            name: 'quantity',
            type: 'number',
            required: true,
            description: 'How many coins to reserve.',
          },
        ],
      },
    ],
  },
];

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>(SEED);
  const [selectedId, setSelectedId] = useState('ag_triage');
  const [tab, setTab] = useState<Tab>('general');
  const [naming, setNaming] = useState(false);
  const [snapshot, setSnapshot] = useState(() => JSON.stringify(SEED));

  const dirty = JSON.stringify(agents) !== snapshot;
  const agent = agents.find((a) => a.id === selectedId) ?? agents[0];
  const isManager = agent?.role === 'manager';
  const others = agents.filter((a) => a.id !== agent?.id);

  // Subagents have no handoffs tab, so fall back rather than show an empty pane.
  const activeTab: Tab = tab === 'handoffs' && !isManager ? 'general' : tab;

  // Patch the selected agent.
  function edit(patch: Partial<Agent>) {
    setAgents((prev) => prev.map((a) => (a.id === agent.id ? { ...a, ...patch } : a)));
  }

  function addAgent(name: string) {
    const id = `ag_${uid()}`;
    setAgents((prev) => [
      ...prev,
      {
        id,
        name,
        role: 'subagent',
        description: '',
        temperature: 0.2,
        maxTokens: 1024,
        prompt: '',
        kbId: '',
        handoffs: [],
        tools: [],
      },
    ]);
    setSelectedId(id);
  }

  function removeAgent(id: string) {
    const left = agents
      .filter((a) => a.id !== id)
      .map((a) => ({ ...a, handoffs: a.handoffs.filter((h) => h.targetId !== id) }));
    setAgents(left);
    if (selectedId === id) setSelectedId(left[0]?.id ?? '');
  }

  function save() {
    if (!agents.every((a) => a.name.trim())) {
      pushToast('Every agent needs a name.');
      return;
    }
    if (agents.some((a) => a.tools.some((t) => !t.name.trim()))) {
      pushToast('Every tool needs a name.');
      return;
    }
    setSnapshot(JSON.stringify(agents));
    pushToast('Saved locally — this screen is a mock.', 'success');
  }

  function reset() {
    setAgents(JSON.parse(snapshot));
  }

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      <Header>
        <Bot size={18} className="text-indigo-600" />
        <h1 className="truncate text-base font-semibold">Agents</h1>
      </Header>

      <div className="flex min-h-0 flex-1 gap-5 px-6 py-5">
        <AgentTopology
          agents={agents}
          selectedId={agent?.id ?? ''}
          onSelect={setSelectedId}
          onAdd={() => setNaming(true)}
          onRemove={removeAgent}
        />

        <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
          {!agent ? (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-400">
              No agents. Add one to get started.
            </div>
          ) : (
            <>
              <div className="flex gap-1 border-b border-slate-200 px-6 pt-1">
                {TABS.filter((t) => t.id !== 'handoffs' || isManager).map((t) => (
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
                {activeTab === 'tools' && <AgentTools agent={agent} onEdit={edit} />}
                {activeTab === 'handoffs' && isManager && (
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
                    disabled={!dirty}
                    className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Save changes
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      </div>

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
