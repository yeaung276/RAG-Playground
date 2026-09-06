import { useState } from 'react';
import { ChevronDown, ChevronRight, Folder, FileText } from 'lucide-react';
import { useNodes } from '../api/knowledge';
import type { FileNode } from '../api/types';

export type Crumb = { id: string; name: string };

interface Props {
  kbId: string;
  selectedId: string | null;
  /** Called when a folder is clicked, with its full path from the root. */
  onSelectFolder: (folderId: string | null, path: Crumb[]) => void;
  /** Called when a file is double-clicked, to open its detail view. */
  onOpenFile: (nodeId: string) => void;
}

export default function FileTree({ kbId, selectedId, onSelectFolder, onOpenFile }: Props) {
  return (
    <div className="min-h-0 flex-1 overflow-auto">
      <button
        onClick={() => onSelectFolder(null, [])}
        className={`flex h-7 w-full items-center gap-1 rounded-md px-2 text-sm ${
          selectedId === null
            ? 'bg-indigo-50 text-indigo-700'
            : 'text-slate-700 hover:bg-slate-100'
        }`}
      >
        <Folder size={15} className="shrink-0 text-indigo-500" />
        <span className="truncate">All files</span>
      </button>
      <Children
        kbId={kbId}
        parentId={null}
        path={[]}
        depth={0}
        selectedId={selectedId}
        onSelectFolder={onSelectFolder}
        onOpenFile={onOpenFile}
      />
    </div>
  );
}

interface ChildrenProps extends Props {
  parentId: string | null;
  path: Crumb[];
  depth: number;
}

function Children({
  kbId,
  parentId,
  path,
  depth,
  selectedId,
  onSelectFolder,
  onOpenFile,
}: ChildrenProps) {
  // Mounts only when its parent folder is open, so the fetch is lazy.
  const { data: nodes, isLoading } = useNodes(kbId, parentId);

  if (isLoading) {
    return (
      <p
        className="py-1 text-xs text-slate-400"
        style={{ paddingLeft: depth * 14 + 26 }}
      >
        Loading…
      </p>
    );
  }

  return (
    <>
      {nodes?.map((n) => (
        <Row
          key={n.id}
          kbId={kbId}
          node={n}
          path={path}
          depth={depth}
          selectedId={selectedId}
          onSelectFolder={onSelectFolder}
          onOpenFile={onOpenFile}
        />
      ))}
    </>
  );
}

interface RowProps extends Props {
  node: FileNode;
  path: Crumb[];
  depth: number;
}

function Row({ kbId, node, path, depth, selectedId, onSelectFolder, onOpenFile }: RowProps) {
  const [open, setOpen] = useState(false);
  const isFolder = node.type === 'folder';
  const nodePath = [...path, { id: node.id, name: node.name }];

  return (
    <>
      <div
        onClick={() => {
          if (!isFolder) return;
          setOpen((o) => !o);
          onSelectFolder(node.id, nodePath);
        }}
        onDoubleClick={() => {
          if (!isFolder) onOpenFile(node.id);
        }}
        title={isFolder ? undefined : 'Double-click for details'}
        style={{ paddingLeft: depth * 14 + 4 }}
        className={`flex h-7 cursor-pointer items-center gap-1 rounded-md pr-2 text-sm ${
          selectedId === node.id
            ? 'bg-indigo-50 text-indigo-700'
            : 'text-slate-700 hover:bg-slate-100'
        }`}
      >
        <span className="flex w-4 shrink-0 justify-center text-slate-400">
          {isFolder ? (
            open ? <ChevronDown size={14} /> : <ChevronRight size={14} />
          ) : null}
        </span>
        {isFolder ? (
          <Folder size={15} className="shrink-0 text-indigo-500" />
        ) : (
          <FileText size={15} className="shrink-0 text-slate-400" />
        )}
        <span className="truncate">{node.name}</span>
      </div>
      {isFolder && open && (
        <Children
          kbId={kbId}
          parentId={node.id}
          path={nodePath}
          depth={depth + 1}
          selectedId={selectedId}
          onSelectFolder={onSelectFolder}
          onOpenFile={onOpenFile}
        />
      )}
    </>
  );
}
