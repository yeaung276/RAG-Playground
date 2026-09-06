import { useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ChevronRight,
  CheckCircle2,
  CircleAlert,
  Download,
  FilePlus2,
  FolderPlus,
  Folder,
  FileText,
  Hourglass,
  RefreshCw,
  RotateCcw,
  Settings2,
  Trash2,
  Upload,
} from 'lucide-react';
import { downloadFile, errorMessage } from '../api/client';
import { pushToast } from '../components/Toast';
import {
  useCreateFolder,
  useDeleteNode,
  useKnowledgeBase,
  useNodes,
  useResyncNode,
  useUploadFiles,
} from '../api/knowledge';
import type { FileNode } from '../api/types';
import { formatBytes, formatDate } from '../utils/format';
import Header from '../components/Header';
import FileTree, { type Crumb } from '../components/FileTree';
import FileDetailDrawer from '../components/FileDetailDrawer';
import NamePromptModal from '../components/NamePromptModal';

/** Small right-aligned indicator reflecting a file's OCR/extraction status. */
function StatusIndicator({ node }: { node: FileNode }) {
  if (node.type !== 'file' || !node.status) return null;
  if (node.status === 'processing') {
    return (
      <span title="Extracting…" className="flex shrink-0 items-center text-amber-500">
        <Hourglass size={13} className="animate-spin" />
      </span>
    );
  }
  if (node.status === 'failed') {
    return (
      <span
        title={node.error ?? 'Extraction failed'}
        className="flex shrink-0 items-center gap-1 text-red-600"
      >
        <CircleAlert size={13} />
        <span className="text-xs font-medium">Failed</span>
      </span>
    );
  }
  if (node.status === 'out_of_sync') {
    return (
      <span
        title="Config changed since extraction — resync to re-process"
        className="flex shrink-0 items-center gap-1 text-amber-600"
      >
        <RotateCcw size={13} />
        <span className="text-xs font-medium">Out of sync</span>
      </span>
    );
  }
  return (
    <span title="Extracted" className="flex shrink-0 items-center text-emerald-500">
      <CheckCircle2 size={13} />
    </span>
  );
}

export default function FileBrowser() {
  const { id } = useParams();
  const kbId = id ?? '';
  const navigate = useNavigate();

  const [path, setPath] = useState<Crumb[]>([]);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const folderId = path.length ? path[path.length - 1].id : null;

  const { data: kb } = useKnowledgeBase(kbId);
  const { data: entries } = useNodes(kbId, folderId);

  const createFolder = useCreateFolder();
  const uploadFiles = useUploadFiles();
  const deleteNode = useDeleteNode();
  const resyncNode = useResyncNode();

  // Mutation/query failures surface through the global toast handler in
  // main.tsx; swallow the rejection here so it isn't an unhandled promise.
  async function run(fn: () => Promise<unknown>) {
    try {
      await fn();
    } catch {
      /* surfaced via toast */
    }
  }

  function enterFolder(node: FileNode) {
    setPath((p) => [...p, { id: node.id, name: node.name }]);
  }

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    await run(() =>
      uploadFiles.mutateAsync({ kbId, parentId: folderId, files: Array.from(files) }),
    );
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    handleUpload(e.dataTransfer.files);
  }

  async function submitFolder(name: string) {
    await run(() => createFolder.mutateAsync({ kbId, parentId: folderId, name }));
  }

  async function download(node: FileNode) {
    // Not a React Query call, so toast its failure explicitly.
    try {
      const blob = await downloadFile(kbId, node.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = node.name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      pushToast(errorMessage(e));
    }
  }

  async function resync(node: FileNode) {
    await run(() => resyncNode.mutateAsync({ kbId, nodeId: node.id }));
  }

  async function remove(node: FileNode) {
    if (!confirm(`Delete "${node.name}"?`)) return;
    await run(() => deleteNode.mutateAsync({ kbId, nodeId: node.id }));
  }

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      <Header
        right={
          <button
            onClick={() => navigate(`/knowledge/${kbId}/config`)}
            title="Configuration"
            className="flex items-center gap-1 rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
          >
            <Settings2 size={16} /> Config
          </button>
        }
      >
        <button
          onClick={() => navigate('/knowledge')}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
        >
          <ArrowLeft size={16} /> Bases
        </button>
        <ChevronRight size={14} className="text-slate-300" />
        <h1 className="truncate text-base font-semibold">{kb?.name ?? '…'}</h1>
      </Header>

      <div className="flex w-full flex-1 gap-4 overflow-hidden px-6 py-4">
        {/* Tree pane */}
        <aside className="flex w-60 shrink-0 flex-col rounded-xl border border-slate-200 bg-white p-2">
          <FileTree
            kbId={kbId}
            selectedId={folderId}
            onSelectFolder={(_, p) => setPath(p)}
            onOpenFile={(nodeId) => setDetailId(nodeId)}
          />
        </aside>

        {/* Detail pane */}
        <section
          onDragEnter={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragOver={(e) => e.preventDefault()}
          onDragLeave={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
          }}
          onDrop={handleDrop}
          className="relative flex min-w-0 flex-1 flex-col rounded-xl border border-slate-200 bg-white"
        >
          {dragging && (
            <div className="pointer-events-none absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-indigo-400 bg-indigo-50/80 text-indigo-600">
              <Upload size={28} />
              <p className="text-sm font-medium">Drop files to upload</p>
            </div>
          )}
          {/* Breadcrumb + actions */}
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-2.5">
            <div className="flex min-w-0 items-center gap-1 text-sm text-slate-600">
              <button
                onClick={() => setPath([])}
                className="rounded px-1.5 py-0.5 font-medium hover:bg-slate-100"
              >
                {kb?.name ?? 'Root'}
              </button>
              {path.map((crumb, i) => (
                <span key={crumb.id} className="flex items-center gap-1">
                  <ChevronRight size={13} className="text-slate-300" />
                  <button
                    onClick={() => setPath(path.slice(0, i + 1))}
                    className="truncate rounded px-1.5 py-0.5 hover:bg-slate-100"
                  >
                    {crumb.name}
                  </button>
                </span>
              ))}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <button
                onClick={() => setNewFolderOpen(true)}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
              >
                <FolderPlus size={15} /> New folder
              </button>
              <button
                onClick={() => fileInput.current?.click()}
                className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-2.5 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
              >
                <Upload size={15} /> Upload
              </button>
              <input
                ref={fileInput}
                type="file"
                multiple
                hidden
                onChange={(e) => {
                  handleUpload(e.target.files);
                  e.target.value = '';
                }}
              />
            </div>
          </div>

          {/* Entry list */}
          <div className="min-h-0 flex-1 overflow-auto">
            {entries && entries.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-slate-400">
                <FilePlus2 size={28} />
                <p className="text-sm">This folder is empty</p>
              </div>
            ) : (
              <table className="w-full table-fixed text-sm">
                <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-4 py-2 font-medium">Name</th>
                    <th className="w-24 px-4 py-2 font-medium">Size</th>
                    <th className="w-28 px-4 py-2 font-medium">Modified</th>
                    <th className="w-20 px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {entries?.map((n) => (
                    <tr
                      key={n.id}
                      onClick={() => n.type === 'folder' && enterFolder(n)}
                      onDoubleClick={() => n.type === 'file' && setDetailId(n.id)}
                      title={n.type === 'file' ? 'Double-click for details' : undefined}
                      className="group cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                    >
                      <td className="px-4 py-2">
                        <div className="flex min-w-0 items-center gap-2">
                          {n.type === 'folder' ? (
                            <Folder size={16} className="shrink-0 text-indigo-500" />
                          ) : (
                            <FileText size={16} className="shrink-0 text-slate-400" />
                          )}
                          <span className="truncate">{n.name}</span>
                          <StatusIndicator node={n} />
                        </div>
                      </td>
                      <td className="px-4 py-2 text-slate-500">
                        {n.type === 'folder' ? '—' : formatBytes(n.size)}
                      </td>
                      <td className="px-4 py-2 text-slate-500">{formatDate(n.updatedAt)}</td>
                      <td className="px-4 py-2">
                        <div
                          onClick={(e) => e.stopPropagation()}
                          onDoubleClick={(e) => e.stopPropagation()}
                          className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100"
                        >
                          {n.type === 'file' && (
                            <>
                              <button
                                onClick={() => download(n)}
                                title="Download"
                                className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
                              >
                                <Download size={14} />
                              </button>
                              <button
                                onClick={() => resync(n)}
                                disabled={n.status === 'processing'}
                                title="Resync"
                                className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-40"
                              >
                                <RefreshCw size={14} />
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => remove(n)}
                            title="Delete"
                            className="rounded p-1 text-slate-400 hover:bg-red-100 hover:text-red-600"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </div>

      <NamePromptModal
        open={newFolderOpen}
        onOpenChange={setNewFolderOpen}
        title="New folder"
        label="Folder name"
        placeholder="e.g. docs"
        onSubmit={submitFolder}
      />

      <FileDetailDrawer kbId={kbId} nodeId={detailId} onClose={() => setDetailId(null)} />
    </div>
  );
}
