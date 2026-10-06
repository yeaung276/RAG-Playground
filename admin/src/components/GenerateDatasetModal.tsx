import { useEffect, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { FileArchive, Sparkles, Tag, Upload, X } from 'lucide-react';
import { z } from 'zod';
import type { Category } from '../api/datasets';
import { useModels } from '../api/models';
import { CATEGORIES, CATEGORY_DOT } from './categories';

const CATEGORY_HINT: Record<Category, string> = {
  simple: 'Answered by one chunk, asked plainly.',
  reasoning: 'Needs an inference over the chunk, not a lookup.',
  multi_context: 'Needs two or more chunks combined.',
  conditional: 'Answer depends on a condition in the question.',
};

const slug = z.string().regex(/^[a-z0-9-]+$/, 'lowercase letters, digits and dashes only');

export const generateDatasetSchema = z.object({
  name: slug.max(48),
  archive: z.instanceof(File, { message: 'Choose a .zip of text files' }),
  /** Chat model that writes the pairs. */
  modelId: z.string().min(1, 'Pick a model'),
  /** Pairs generated per file in the archive. */
  samplePerFile: z.number().int().min(1).max(10),
  /** Percent share per category; the four must total exactly 100. */
  mix: z
    .record(z.enum(CATEGORIES), z.number().min(0).max(100))
    .refine(
      (m) => CATEGORIES.reduce((sum, c) => sum + (m[c] ?? 0), 0) === 100,
      'Category mix must add up to 100%',
    ),
  labels: z.array(slug.max(24)),
});

export type GenerateDatasetValues = z.infer<typeof generateDatasetSchema>;

/** Form state before validation: the archive is still unset and the mix may not total 100. */
type Draft = Omit<GenerateDatasetValues, 'archive'> & { archive: File | null };

const EMPTY: Draft = {
  name: '',
  archive: null,
  modelId: '',
  samplePerFile: 3,
  mix: { simple: 40, reasoning: 25, multi_context: 25, conditional: 10 },
  labels: [],
};

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (values: GenerateDatasetValues) => Promise<void> | void;
  defaultValues?: Partial<Draft>;
}

const input =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100';

export default function GenerateDatasetModal({
  open,
  onClose,
  onSubmit,
  defaultValues,
}: Props) {
  const [values, setValues] = useState<Draft>(EMPTY);
  const [draft, setDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setValues({ ...EMPTY, ...defaultValues });
    setDraft('');
    setSubmitting(false);
    setError(null);
    // defaultValues is read once per opening; a new object identity must not reset the form
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const { data: models } = useModels(1, 'decoder', 100);

  const { name, archive, modelId, samplePerFile, mix, labels } = values;
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setValues((v) => ({ ...v, [key]: value }));

  const spent = CATEGORIES.reduce((sum, c) => sum + mix[c], 0);
  const parsed = generateDatasetSchema.safeParse(values);

  const addLabel = () => {
    const label = draft.trim();
    if (!/^[a-z0-9-]+$/.test(label) || labels.includes(label)) return;
    set('labels', [...labels, label]);
    setDraft('');
  };

  async function submit() {
    if (submitting) return;
    if (!parsed.success) {
      setError(parsed.error.issues[0].message);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(parsed.data);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
      setSubmitting(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(next) => !next && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed left-1/2 top-1/2 flex max-h-[85vh] w-[90vw] max-w-lg -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
          <div className="border-b border-slate-100 px-6 py-5">
            <Dialog.Title className="text-base font-semibold">Generate dataset</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-slate-500">
              Each pair is a question, its reference answer, and the chunk it came from.
              Generation runs in the background.
            </Dialog.Description>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            <div className="min-h-0 flex-1 space-y-7 overflow-y-auto px-6 py-5">
              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Source
                </h3>

                <label className="block cursor-pointer">
                  <input
                    type="file"
                    accept=".zip"
                    className="sr-only"
                    onChange={(e) => set('archive', e.target.files?.[0] ?? null)}
                  />
                  {archive ? (
                    <span className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
                      <FileArchive size={20} className="shrink-0 text-slate-400" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-slate-700">
                          {archive.name}
                        </span>
                        <span className="block text-xs text-slate-400">
                          {formatSize(archive.size)}
                        </span>
                      </span>
                      <span className="text-xs font-medium text-slate-500 underline">Replace</span>
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 px-3 py-6 text-sm text-slate-500 transition hover:border-indigo-400 hover:text-indigo-600">
                      <Upload size={16} /> Choose a .zip of text files
                    </span>
                  )}
                </label>

                <Field label="Dataset name" hint="lowercase, no spaces">
                  <input
                    className={input}
                    placeholder="support-faq-v4"
                    pattern="[a-z0-9-]+"
                    maxLength={48}
                    required
                    value={name}
                    onChange={(e) => set('name', e.target.value)}
                  />
                </Field>

                <div className="grid grid-cols-[1fr_auto] gap-3">
                  <Field label="Model" hint="writes the pairs">
                    <select
                      className={input}
                      value={modelId}
                      onChange={(e) => set('modelId', e.target.value)}
                    >
                      <option value="">Select a chat model</option>
                      {models?.items.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.provider} · {m.name}
                        </option>
                      ))}
                    </select>
                  </Field>

                  <Field label="Questions per file" hint="1–10">
                    <span className="flex w-36 items-center rounded-lg border border-slate-300 bg-white pr-2.5 transition focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100">
                      <input
                        type="number"
                        min={1}
                        max={10}
                        required
                        value={samplePerFile}
                        onChange={(e) =>
                          set('samplePerFile', Math.min(Math.max(Number(e.target.value), 1), 10))
                        }
                        className="w-full [appearance:textfield] bg-transparent px-3 py-2 text-sm tabular-nums outline-none [&::-webkit-inner-spin-button]:appearance-none"
                      />
                      <span className="shrink-0 whitespace-nowrap text-xs text-slate-400">
                        per file
                      </span>
                    </span>
                  </Field>
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="flex items-baseline gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Category mix
                  <span
                    className={`ml-auto tabular-nums normal-case tracking-normal ${
                      spent === 100 ? 'text-slate-400' : 'text-amber-600'
                    }`}
                  >
                    {spent === 100 ? 'spent' : `${100 - spent}% left`}
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  How each question is evolved from its chunk. A share can only take the percent the
                  others have left, and all four must add up to 100%.
                </p>

                <div className="flex h-2.5 overflow-hidden rounded-full bg-slate-100">
                  {CATEGORIES.map((c) => (
                    <span key={c} className={CATEGORY_DOT[c]} style={{ width: `${mix[c]}%` }} />
                  ))}
                </div>

                <div className="space-y-3 pt-1">
                  {CATEGORIES.map((c) => {
                    const cap = 100 - (spent - mix[c]);
                    return (
                      <div key={c}>
                        <div className="flex items-baseline gap-2">
                          <span className={`size-2 shrink-0 rounded-full ${CATEGORY_DOT[c]}`} />
                          <span className="text-sm font-medium text-slate-700">{c}</span>
                          <span className="ml-auto text-xs tabular-nums text-slate-500">
                            {mix[c]}%
                          </span>
                        </div>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          value={mix[c]}
                          onChange={(e) =>
                            set('mix', { ...mix, [c]: Math.min(Number(e.target.value), cap) })
                          }
                          aria-label={`${c} share`}
                          className="mt-1 w-full accent-indigo-600"
                        />
                        <p className="text-xs text-slate-400">{CATEGORY_HINT[c]}</p>
                      </div>
                    );
                  })}
                </div>
              </section>

              <section className="space-y-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Labels
                </h3>
                <p className="text-xs text-slate-400">
                  Your own tags, matched as each pair is written. A pair can carry several, or none.
                </p>

                {labels.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {labels.map((label) => (
                      <span
                        key={label}
                        className="flex items-center gap-1.5 rounded-lg border border-slate-200 py-1.5 pl-2.5 pr-1.5 text-sm font-medium text-slate-700"
                      >
                        <Tag size={13} className="shrink-0 text-indigo-500" />
                        {label}
                        <button
                          type="button"
                          onClick={() => set('labels', labels.filter((l) => l !== label))}
                          aria-label={`remove ${label}`}
                          className="text-slate-300 hover:text-red-500"
                        >
                          <X size={14} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex gap-2">
                  <input
                    className={input}
                    placeholder="label"
                    pattern="[a-z0-9-]+"
                    maxLength={24}
                    aria-label="new label"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        addLabel();
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={addLabel}
                    className="shrink-0 rounded-lg border border-slate-300 px-3 text-sm font-medium text-slate-600 hover:bg-slate-50"
                  >
                    Add
                  </button>
                </div>
              </section>

              {error && <p className="text-sm text-red-600">{error}</p>}
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-100 px-6 py-4">
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!parsed.success || submitting}
                className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Sparkles size={16} /> {submitting ? 'Generating…' : 'Generate'}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline gap-2">
        <span className="text-sm font-medium text-slate-700">{label}</span>
        {hint && <span className="ml-auto text-xs text-slate-400">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

function formatSize(bytes: number) {
  const mb = bytes / 1024 / 1024;
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}
