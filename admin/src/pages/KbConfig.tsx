import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ChevronRight, Layers } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useKnowledgeBase, useUpdateKnowledgeBaseConfig } from '../api/knowledge';
import {
  CHUNKING_METHODS,
  INDEX_TYPES,
  configFieldErrors,
  type ChunkingMethod,
  type KnowledgeBaseConfig,
} from '../api/config';
import { pushToast } from '../components/Toast';
import Header from '../components/Header';

type FieldErrors = Partial<Record<keyof KnowledgeBaseConfig, string>>;

// Config sections drive the left menu. Adding a new panel = one entry here plus
// a case in <SectionBody>. `fields` lets the menu flag which section holds an
// invalid value.
interface Section {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
  fields: (keyof KnowledgeBaseConfig)[];
}

const SECTIONS: Section[] = [
  {
    id: 'indexing',
    label: 'Indexing',
    description: 'How documents are chunked and embedded for retrieval.',
    icon: Layers,
    fields: ['chunkingMethod', 'maxChunkSize', 'minChunkSize', 'indexTypes'],
  },
];

export default function KbConfig() {
  const { id } = useParams();
  const kbId = id ?? '';
  const navigate = useNavigate();

  const { data: kb } = useKnowledgeBase(kbId);
  const updateConfig = useUpdateKnowledgeBaseConfig();

  const [form, setForm] = useState<KnowledgeBaseConfig | null>(null);
  const [active, setActive] = useState(SECTIONS[0].id);

  // Seed the form once the base loads.
  useEffect(() => {
    if (kb) setForm(kb.config);
  }, [kb]);

  const errors: FieldErrors = form ? configFieldErrors(form) : {};
  const valid = !!form && Object.values(errors).every((e) => !e);
  // Index types are a set, so order changes from toggling are not a change.
  const dirty =
    !!kb &&
    !!form &&
    (form.chunkingMethod !== kb.config.chunkingMethod ||
      form.maxChunkSize !== kb.config.maxChunkSize ||
      form.minChunkSize !== kb.config.minChunkSize ||
      form.indexTypes.length !== kb.config.indexTypes.length ||
      form.indexTypes.some((t) => !kb.config.indexTypes.includes(t)));

  function sectionHasError(s: Section) {
    return s.fields.some((f) => errors[f]);
  }

  async function save() {
    if (!form || !valid || !dirty) return;
    try {
      await updateConfig.mutateAsync({ kbId, config: form });
      pushToast('Configuration saved. Extracted files marked out of sync.', 'success');
      navigate(`/knowledge/${kbId}`);
    } catch {
      /* surfaced via the global toast handler */
    }
  }

  const activeSection = SECTIONS.find((s) => s.id === active) ?? SECTIONS[0];

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      <Header>
        <button
          onClick={() => navigate('/knowledge')}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
        >
          <ArrowLeft size={16} /> Bases
        </button>
        <ChevronRight size={14} className="text-slate-300" />
        <button
          onClick={() => navigate(`/knowledge/${kbId}`)}
          className="truncate rounded-md px-2 py-1 text-base font-semibold hover:bg-slate-100"
        >
          {kb?.name ?? '…'}
        </button>
        <ChevronRight size={14} className="text-slate-300" />
        <span className="text-sm text-slate-500">Configuration</span>
      </Header>

      <div className="mx-auto flex w-full max-w-5xl flex-1 gap-6 overflow-hidden px-6 py-6">
        {/* Left menu */}
        <nav className="w-52 shrink-0 space-y-1">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            const selected = s.id === active;
            return (
              <button
                key={s.id}
                onClick={() => setActive(s.id)}
                className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${
                  selected
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Icon size={16} className="shrink-0" />
                <span className="flex-1 text-left">{s.label}</span>
                {sectionHasError(s) && (
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-red-500" />
                )}
              </button>
            );
          })}
        </nav>

        {/* Right form */}
        <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-6 py-4">
            <h2 className="text-base font-semibold">{activeSection.label}</h2>
            <p className="mt-0.5 text-sm text-slate-500">{activeSection.description}</p>
          </div>

          <div className="min-h-0 flex-1 overflow-auto px-6 py-5">
            {!form ? (
              <p className="text-sm text-slate-400">Loading…</p>
            ) : (
              <SectionBody
                section={activeSection.id}
                form={form}
                errors={errors}
                onChange={setForm}
              />
            )}
          </div>

          {/* Save bar — always visible; Save enables once there are valid changes. */}
          <div className="flex items-center justify-between gap-4 border-t border-slate-200 bg-slate-50 px-6 py-3">
            <p className="text-xs text-slate-500">
              {dirty ? (
                <>
                  Saving marks extracted files{' '}
                  <span className="font-medium text-amber-700">out of sync</span>.
                </>
              ) : (
                'No unsaved changes.'
              )}
            </p>
            <div className="flex shrink-0 gap-2">
              <button
                onClick={() => kb && setForm(kb.config)}
                disabled={!dirty}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Reset
              </button>
              <button
                onClick={save}
                disabled={!dirty || !valid || updateConfig.isPending}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {updateConfig.isPending ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function SectionBody({
  section,
  form,
  errors,
  onChange,
}: {
  section: string;
  form: KnowledgeBaseConfig;
  errors: FieldErrors;
  onChange: (config: KnowledgeBaseConfig) => void;
}) {
  if (section === 'indexing') {
    return (
      <div className="max-w-xl space-y-8">
        <Group label="Chunking">
          <Field
            label="Chunking method"
            description="How documents are split into parent chunks."
            error={errors.chunkingMethod}
          >
            <select
              value={form.chunkingMethod}
              onChange={(e) =>
                onChange({ ...form, chunkingMethod: e.target.value as ChunkingMethod })
              }
              className="w-56 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            >
              {CHUNKING_METHODS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="Parent chunk size"
            description="Tokens per parent chunk retrieved for context."
            error={errors.maxChunkSize}
          >
            <NumberInput
              value={form.maxChunkSize}
              invalid={!!errors.maxChunkSize}
              onChange={(v) => onChange({ ...form, maxChunkSize: v })}
            />
          </Field>
          <Field
            label="Child chunk size"
            description="Tokens per child chunk used for embedding & search; must be smaller than parent."
            error={errors.minChunkSize}
          >
            <NumberInput
              value={form.minChunkSize}
              invalid={!!errors.minChunkSize}
              onChange={(v) => onChange({ ...form, minChunkSize: v })}
            />
          </Field>
        </Group>

        <Group label="Indexing">
          <Field
            label="Index types"
            description="Indexes built over the chunks. Changing these rebuilds the collection and re-indexes every file."
            error={errors.indexTypes}
          >
            <div className="flex w-56 flex-col gap-1.5">
              {INDEX_TYPES.map((t) => (
                <label key={t} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={form.indexTypes.includes(t)}
                    onChange={(e) =>
                      onChange({
                        ...form,
                        indexTypes: e.target.checked
                          ? [...form.indexTypes, t]
                          : form.indexTypes.filter((i) => i !== t),
                      })
                    }
                    className="accent-indigo-600"
                  />
                  {t}
                </label>
              ))}
            </div>
          </Field>
        </Group>
      </div>
    );
  }

  return null;
}

/** A labelled group of related settings within a section panel. */
function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <div className="divide-y divide-slate-100">{children}</div>
    </div>
  );
}

/** One setting: label + description on the left, control on the right. */
function Field({
  label,
  description,
  error,
  children,
}: {
  label: string;
  description: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
      <div className="min-w-0 sm:pt-1.5">
        <p className="text-sm font-medium text-slate-700">{label}</p>
        <p className="mt-0.5 text-[11px] text-slate-400">{description}</p>
      </div>
      <div className="flex shrink-0 flex-col items-start gap-1 sm:items-end">
        {children}
        {error && <span className="text-[11px] text-red-600">{error}</span>}
      </div>
    </div>
  );
}

function NumberInput({
  value,
  invalid,
  onChange,
}: {
  value: number;
  invalid: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <input
      type="number"
      min={1}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      aria-invalid={invalid}
      className={`w-36 rounded-lg border px-3 py-2 text-sm outline-none focus:ring-1 ${
        invalid
          ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
          : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500'
      }`}
    />
  );
}
