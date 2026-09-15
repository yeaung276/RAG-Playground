import { useEffect, useRef, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import {
  CHUNKING_METHODS,
  DEFAULT_CONFIG,
  INDEX_TYPES,
  configFieldErrors,
  type ChunkingMethod,
  type KnowledgeBaseConfig,
} from '../api/config';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (name: string, config: KnowledgeBaseConfig) => Promise<void>;
}

export default function NewKbModal({ open, onOpenChange, onSubmit }: Props) {
  const [name, setName] = useState('');
  const [config, setConfig] = useState<KnowledgeBaseConfig>(DEFAULT_CONFIG);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setName('');
      setConfig(DEFAULT_CONFIG);
      setError(null);
      setBusy(false);
    }
  }, [open]);

  const errors = configFieldErrors(config);
  const configValid = Object.values(errors).every((e) => !e);
  const valid = name.trim().length > 0 && configValid;

  async function submit() {
    if (!valid) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit(name.trim(), config);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
      setBusy(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 w-[90vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-5 shadow-xl focus:outline-none"
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            nameRef.current?.focus();
          }}
        >
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className="text-base font-semibold text-slate-900">
              New knowledge
            </Dialog.Title>
            <Dialog.Close className="text-slate-400 hover:text-slate-600">
              <X size={18} />
            </Dialog.Close>
          </div>

          <div className="flex flex-col gap-4">
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-slate-600">Name</span>
              <input
                ref={nameRef}
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') submit();
                }}
                placeholder="e.g. Coin regulations"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <NumberField
                label="Parent chunk size"
                value={config.maxChunkSize}
                onChange={(v) => setConfig({ ...config, maxChunkSize: v })}
                hint="Tokens per parent chunk kept for context."
                error={errors.maxChunkSize}
              />
              <NumberField
                label="Child chunk size"
                value={config.minChunkSize}
                onChange={(v) => setConfig({ ...config, minChunkSize: v })}
                hint="Tokens per child chunk; must be smaller than parent."
                error={errors.minChunkSize}
              />
            </div>

            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-slate-600">Chunking method</span>
              <select
                value={config.chunkingMethod}
                onChange={(e) =>
                  setConfig({ ...config, chunkingMethod: e.target.value as ChunkingMethod })
                }
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                {CHUNKING_METHODS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <span className="text-[11px] text-slate-400">
                How documents are split into parent chunks.
              </span>
            </label>

            <div className="flex flex-col gap-1">
              <span className="text-sm font-medium text-slate-600">Index types</span>
              <div className="flex flex-col gap-1.5 rounded-lg border border-slate-300 px-3 py-2">
                {INDEX_TYPES.map((t) => (
                  <label key={t} className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={config.indexTypes.includes(t)}
                      onChange={(e) =>
                        setConfig({
                          ...config,
                          indexTypes: e.target.checked
                            ? [...config.indexTypes, t]
                            : config.indexTypes.filter((i) => i !== t),
                        })
                      }
                      className="accent-indigo-600"
                    />
                    {t}
                  </label>
                ))}
              </div>
              <span className={`text-[11px] ${errors.indexTypes ? 'text-red-600' : 'text-slate-400'}`}>
                {errors.indexTypes ?? 'Indexes built for search. Fixed once the base is created.'}
              </span>
            </div>
          </div>

          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

          <div className="mt-5 flex justify-end gap-2">
            <Dialog.Close className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">
              Cancel
            </Dialog.Close>
            <button
              onClick={submit}
              disabled={busy || !valid}
              className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? 'Creating…' : 'Create'}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function NumberField({
  label,
  value,
  onChange,
  hint,
  error,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  hint: string;
  error?: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm font-medium text-slate-600">{label}</span>
      <input
        type="number"
        min={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-invalid={!!error}
        className={`w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-1 ${
          error
            ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
            : 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500'
        }`}
      />
      <span className={`text-[11px] ${error ? 'text-red-600' : 'text-slate-400'}`}>
        {error ?? hint}
      </span>
    </label>
  );
}
