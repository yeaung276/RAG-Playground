import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import {
  ArrowDownWideNarrow,
  Boxes,
  KeyRound,
  Link2,
  Pencil,
  MessageSquareText,
  Plus,
  Trash2,
  Waypoints,
} from 'lucide-react';
import Header from '../components/Header';
import {
  CAPABILITY_LABELS,
  SCHEMA_CAPABILITIES,
  useCreateModel,
  useDeleteModel,
  useModels,
  useUpdateModel,
  type ApiSchema,
  type Capability,
  type Model,
  type ModelInput,
} from '../api/models';

const SCHEMAS = Object.keys(SCHEMA_CAPABILITIES) as ApiSchema[];
const CAPABILITIES = Object.keys(CAPABILITY_LABELS) as Capability[];
const PAGE_SIZE = 20;

const CAPABILITY_ICONS = {
  'bi-encoder': Waypoints,
  'cross-encoder': ArrowDownWideNarrow,
  decoder: MessageSquareText,
} satisfies Record<Capability, typeof Waypoints>;

const CAPABILITY_STYLES: Record<Capability, { tile: string; pill: string }> = {
  'bi-encoder': {
    tile: 'bg-gradient-to-br from-sky-400 to-cyan-500',
    pill: 'bg-sky-50 text-sky-700',
  },
  'cross-encoder': {
    tile: 'bg-gradient-to-br from-amber-400 to-orange-500',
    pill: 'bg-amber-50 text-amber-700',
  },
  decoder: {
    tile: 'bg-gradient-to-br from-violet-500 to-fuchsia-500',
    pill: 'bg-violet-50 text-violet-700',
  },
};

const EMPTY: ModelInput = {
  provider: '',
  schema: 'openai',
  baseUrl: '',
  apiKey: '',
  name: '',
  capability: 'decoder',
};

const input =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100';

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      <span className="mt-1 block text-xs text-slate-400">{hint}</span>
    </label>
  );
}

export default function Models() {
  const [filter, setFilter] = useState<Capability | 'all'>('all');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Model | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);

  const { data, isLoading } = useModels(page, filter, PAGE_SIZE);
  const create = useCreateModel();
  const update = useUpdateModel();
  const remove = useDeleteModel();

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const allowed = SCHEMA_CAPABILITIES[form.schema];

  function pick(capability: Capability | 'all') {
    setFilter(capability);
    setPage(1);
  }

  /** Capability is constrained by schema — reset it when the schema no longer serves it. */
  function pickSchema(schema: ApiSchema) {
    const capabilities = SCHEMA_CAPABILITIES[schema];
    setForm({
      ...form,
      schema,
      capability: capabilities.includes(form.capability) ? form.capability : capabilities[0],
    });
  }

  function startAdd() {
    setEditing(null);
    setForm(EMPTY);
    setOpen(true);
  }

  function startEdit(model: Model) {
    setEditing(model);
    // The stored key is never sent back; blank means "keep it".
    setForm({ ...model, apiKey: '' });
    setOpen(true);
  }

  function close() {
    setOpen(false);
    setEditing(null);
    setForm(EMPTY);
  }

  function submit() {
    if (editing) {
      const { provider, baseUrl, name, apiKey } = form;
      update.mutate(
        { id: editing.id, patch: { provider, baseUrl, name, ...(apiKey ? { apiKey } : {}) } },
        { onSuccess: close },
      );
      return;
    }
    create.mutate({ ...form, apiKey: form.apiKey || null }, { onSuccess: close });
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header>
        <Boxes size={18} className="text-indigo-600" />
        <h1 className="truncate text-base font-semibold">Models</h1>
      </Header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex gap-1">
            {(['all', ...CAPABILITIES] as const).map((c) => {
              const Icon = c === 'all' ? Boxes : CAPABILITY_ICONS[c];
              return (
                <button
                  key={c}
                  onClick={() => pick(c)}
                  className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition ${
                    filter === c
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-500 hover:bg-slate-100'
                  }`}
                >
                  <Icon size={14} />
                  {c === 'all' ? 'All' : CAPABILITY_LABELS[c]}
                </button>
              );
            })}
          </div>
          <button
            onClick={startAdd}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus size={16} /> Add model
          </button>
        </div>

        {!isLoading && items.length === 0 && (
          <p className="rounded-xl border border-dashed border-slate-200 py-16 text-center text-sm text-slate-400">
            No models yet.
          </p>
        )}

        <div className="mb-6 grid gap-4 sm:grid-cols-2">
          {items.map((m) => {
            const style = CAPABILITY_STYLES[m.capability];
            const Icon = CAPABILITY_ICONS[m.capability];
            return (
              <article
                key={m.id}
                className="group rounded-2xl border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-md"
              >
                <div className="flex items-start gap-3.5">
                  <span
                    className={`flex size-11 shrink-0 items-center justify-center rounded-xl text-white shadow-sm ${style.tile}`}
                  >
                    <Icon size={20} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold">{m.name}</h3>
                    <p className="mt-0.5 truncate text-xs text-slate-500">{m.provider}</p>
                  </div>
                  <div className="flex gap-0.5 opacity-0 transition group-hover:opacity-100">
                    <button
                      onClick={() => startEdit(m)}
                      className="rounded-lg p-1 text-slate-300 transition hover:bg-indigo-50 hover:text-indigo-600"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      onClick={() => remove.mutate(m.id)}
                      className="rounded-lg p-1 text-slate-300 transition hover:bg-red-50 hover:text-red-500"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-1.5">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${style.pill}`}
                  >
                    {CAPABILITY_LABELS[m.capability]}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                    {m.schema}
                  </span>
                  {m.hasApiKey && (
                    <span className="flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
                      <KeyRound size={12} /> Key
                    </span>
                  )}
                </div>

                <div className="mt-4 flex items-center gap-1.5 border-t border-slate-100 pt-3 text-xs text-slate-400">
                  <Link2 size={12} className="shrink-0" />
                  <span className="truncate font-mono">{m.baseUrl}</span>
                </div>
              </article>
            );
          })}
        </div>

        {pages > 1 && (
          <div className="flex items-center justify-end gap-2 text-sm text-slate-500">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="rounded-lg px-3 py-1.5 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-transparent"
            >
              Previous
            </button>
            <span>
              {page} / {pages}
            </span>
            <button
              disabled={page === pages}
              onClick={() => setPage(page + 1)}
              className="rounded-lg px-3 py-1.5 hover:bg-slate-100 disabled:opacity-40 disabled:hover:bg-transparent"
            >
              Next
            </button>
          </div>
        )}
      </main>

      <Dialog.Root open={open} onOpenChange={(o) => (o ? setOpen(true) : close())}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-1/2 top-1/2 flex max-h-[85vh] w-[90vw] max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
            <div className="border-b border-slate-100 px-6 py-5">
              <Dialog.Title className="text-base font-semibold">
                {editing ? 'Edit model' : 'Add model'}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-slate-500">
                {editing
                  ? 'Schema and capability are fixed once a model is created.'
                  : 'Point at an endpoint and name the model it serves.'}
              </Dialog.Description>
            </div>

            <div className="flex-1 space-y-6 overflow-y-auto px-6 py-5">
              <section className="space-y-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Connection
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Provider" hint="Label used to group models in the list.">
                    <input
                      className={input}
                      placeholder="OpenAI"
                      value={form.provider}
                      onChange={(e) => setForm({ ...form, provider: e.target.value })}
                    />
                  </Field>
                  <Field label="API schema" hint="Which API dialect the endpoint speaks.">
                    <select
                      className={`${input} disabled:bg-slate-50 disabled:text-slate-400`}
                      value={form.schema}
                      disabled={!!editing}
                      onChange={(e) => pickSchema(e.target.value as ApiSchema)}
                    >
                      {SCHEMAS.map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </Field>
                </div>
                <Field label="Base URL" hint="Root of the API, without the route path.">
                  <input
                    className={input}
                    placeholder="https://api.openai.com/v1"
                    value={form.baseUrl}
                    onChange={(e) => setForm({ ...form, baseUrl: e.target.value })}
                  />
                </Field>
                <Field
                  label="API key"
                  hint={
                    editing
                      ? 'Leave blank to keep the stored key.'
                      : 'Leave empty for endpoints that need no auth.'
                  }
                >
                  <input
                    className={input}
                    type="password"
                    placeholder="sk-..."
                    value={form.apiKey ?? ''}
                    onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
                  />
                </Field>
              </section>

              <section className="space-y-4 border-t border-slate-100 pt-6">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Model
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Model name" hint="Exact identifier sent to the provider.">
                    <input
                      className={input}
                      placeholder="text-embedding-3-small"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                    />
                  </Field>
                  <Field label="Capability" hint="Limited to what this schema serves.">
                    <select
                      className={`${input} disabled:bg-slate-50 disabled:text-slate-400`}
                      value={form.capability}
                      disabled={!!editing}
                      onChange={(e) =>
                        setForm({ ...form, capability: e.target.value as Capability })
                      }
                    >
                      {allowed.map((c) => (
                        <option key={c} value={c}>
                          {CAPABILITY_LABELS[c]}
                        </option>
                      ))}
                    </select>
                  </Field>
                </div>
              </section>
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-100 bg-slate-50 px-6 py-4">
              <Dialog.Close className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
                Cancel
              </Dialog.Close>
              <button
                onClick={submit}
                disabled={
                  !form.provider ||
                  !form.baseUrl ||
                  !form.name ||
                  create.isPending ||
                  update.isPending
                }
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {create.isPending || update.isPending
                  ? 'Saving…'
                  : editing
                    ? 'Save changes'
                    : 'Add model'}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
