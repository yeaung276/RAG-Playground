import * as Dialog from '@radix-ui/react-dialog';
import {
  CheckCircle2,
  CircleAlert,
  FileText,
  Hourglass,
  RotateCcw,
  X,
} from 'lucide-react';
import { errorMessage } from '../api/client';
import { useFileDetail } from '../api/knowledge';
import type { FileNode } from '../api/types';
import { formatBytes, formatDate } from '../utils/format';
import ChunkedMarkdown from './ChunkedMarkdown';

interface Props {
  kbId: string;
  nodeId: string | null;
  onClose: () => void;
}

function fileTypeLabel(mime: string | null, name: string): string {
  if (mime === 'application/pdf') return 'PDF';
  if (mime?.startsWith('image/')) return 'IMG';
  if (mime?.startsWith('text/')) return 'TXT';
  const ext = name.includes('.') ? name.split('.').pop() : '';
  return ext ? ext.toUpperCase().slice(0, 5) : 'FILE';
}

function SyncPill({ node }: { node: FileNode }) {
  if (node.status === 'processing') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
        <Hourglass size={12} className="animate-spin" /> Processing…
      </span>
    );
  }
  if (node.status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">
        <CircleAlert size={12} /> Failed
      </span>
    );
  }
  if (node.status === 'completed') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
        <CheckCircle2 size={12} /> Extracted
      </span>
    );
  }
  if (node.status === 'out_of_sync') {
    return (
      <span
        title="Config changed since extraction — resync to re-process"
        className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700"
      >
        <RotateCcw size={12} /> Out of sync
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500">
      Not extracted
    </span>
  );
}

function ConfigRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="truncate text-xs font-medium text-slate-700">{value}</dd>
    </div>
  );
}

function MetaField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wide text-slate-400">{label}</span>
      <span className="text-sm text-slate-700">{children}</span>
    </div>
  );
}

export default function FileDetailDrawer({ kbId, nodeId, onClose }: Props) {
  const open = nodeId !== null;
  const { data, isLoading, error } = useFileDetail(kbId, nodeId);

  return (
    <Dialog.Root modal={false} open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal forceMount>
        <Dialog.Overlay
          forceMount
          className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity duration-200 data-[state=open]:opacity-100 data-[state=closed]:pointer-events-none data-[state=closed]:opacity-0"
        />
        <Dialog.Content
          forceMount
          aria-describedby={undefined}
          className="fixed right-0 top-0 flex h-full w-[92vw] flex-col bg-white shadow-2xl transition-transform duration-300 ease-out focus:outline-none data-[state=open]:translate-x-0 data-[state=closed]:pointer-events-none data-[state=closed]:translate-x-full sm:w-1/3 sm:min-w-[560px]"
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
            <div className="flex min-w-0 items-center gap-2">
              <FileText size={18} className="shrink-0 text-slate-400" />
              <Dialog.Title className="truncate text-base font-semibold text-slate-900">
                {data?.name ?? 'File'}
              </Dialog.Title>
            </div>
            <Dialog.Close
              className="shrink-0 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              aria-label="Close"
            >
              <X size={18} />
            </Dialog.Close>
          </div>

          {/* Metadata */}
          <div className="border-b border-slate-200 px-5 py-4">
            <div className="grid grid-cols-3 gap-4">
              <MetaField label="Type">
                {data ? (
                  <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600">
                    {fileTypeLabel(data.mimeType, data.name)}
                  </span>
                ) : (
                  '—'
                )}
              </MetaField>
              <MetaField label="Size">{data ? formatBytes(data.size) : '—'}</MetaField>
              <MetaField label="Sync">{data ? <SyncPill node={data} /> : '—'}</MetaField>
            </div>
            {data?.status === 'failed' && data.error && (
              <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
                {data.error}
              </p>
            )}
            {data && (
              <p className="mt-3 text-xs text-slate-400">
                Modified {formatDate(data.updatedAt)}
              </p>
            )}
          </div>

          {/* Indexing config snapshot used to process this file */}
          {data?.config && (
            <div className="border-b border-slate-200 px-5 py-4">
              <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Config
              </h4>
              <dl className="space-y-1">
                <ConfigRow label="Parent chunk size" value={data.config.parentChunkSize} />
                <ConfigRow label="Child chunk size" value={data.config.childChunkSize} />
                <ConfigRow label="Embedding model" value={data.config.embeddingModel} />
              </dl>
            </div>
          )}

          {/* Extracted content */}
          <div className="flex items-center justify-between px-5 pt-4 pb-2">
            <h3 className="text-sm font-medium text-slate-600">Extracted content</h3>
            {data && data.chunks.length > 0 && (
              <span className="text-xs text-slate-400">
                {data.chunks.length} chunk{data.chunks.length === 1 ? '' : 's'}
              </span>
            )}
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-5 pb-5">
            {isLoading && <p className="text-sm text-slate-400">Loading…</p>}
            {error && (
              <p className="text-sm text-red-600">{errorMessage(error)}</p>
            )}
            {data && data.status === 'processing' && (
              <div className="flex items-center gap-2 text-sm text-amber-600">
                <Hourglass size={14} className="animate-spin" /> Extracting content…
              </div>
            )}
            {data &&
              data.status !== 'processing' &&
              data.chunks.length === 0 &&
              !error && (
                <p className="text-sm text-slate-400">
                  {data.status === 'failed'
                    ? 'Extraction failed — no content available.'
                    : 'No extracted content for this file.'}
                </p>
              )}
            {data && data.chunks.length > 0 && (
              <ChunkedMarkdown chunks={data.chunks} />
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
