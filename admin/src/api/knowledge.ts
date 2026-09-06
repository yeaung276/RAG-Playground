import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { request } from './client';
import type {
  FileDetail,
  FileNode,
  KnowledgeBase,
  KnowledgeBaseConfig,
} from './types';

// Poll cadence while any file is still being extracted.
const POLL_MS = 2000;

/** Query key factory — keeps invalidation call sites in sync. */
export const keys = {
  kbList: ['knowledge', 'kb'] as const,
  kb: (id: string) => ['knowledge', 'kb', id] as const,
  // Prefix for a KB's folder listings; a specific folder appends its parent id.
  nodes: (kbId: string) => ['knowledge', 'kb', kbId, 'nodes'] as const,
  file: (kbId: string, nodeId: string) =>
    ['knowledge', 'kb', kbId, 'file', nodeId] as const,
};

// ── Queries ─────────────────────────────────────────────────────────────

export function useKnowledgeBases() {
  return useQuery({
    queryKey: keys.kbList,
    queryFn: () => request<KnowledgeBase[]>(''),
  });
}

export function useKnowledgeBase(id: string) {
  return useQuery({
    queryKey: keys.kb(id),
    queryFn: () => request<KnowledgeBase>(`/${id}`),
    enabled: !!id,
  });
}

/** Children of a folder (root when parentId is null). Lazily fetched per folder. */
export function useNodes(kbId: string, parentId: string | null) {
  const q = parentId ? `?parent=${encodeURIComponent(parentId)}` : '';
  return useQuery({
    queryKey: [...keys.nodes(kbId), parentId ?? 'root'],
    queryFn: () => request<FileNode[]>(`/${kbId}/nodes${q}`),
    enabled: !!kbId,
    // Poll only while a child is still processing; stop once all settle.
    refetchInterval: (query) =>
      query.state.data?.some((n) => n.status === 'processing') ? POLL_MS : false,
  });
}

export function useFileDetail(kbId: string, nodeId: string | null) {
  return useQuery({
    queryKey: keys.file(kbId, nodeId ?? ''),
    queryFn: () => request<FileDetail>(`/${kbId}/files/${nodeId}`),
    enabled: !!kbId && !!nodeId,
    // Poll only while the file is still processing; stop once it settles.
    refetchInterval: (query) =>
      query.state.data?.status === 'processing' ? POLL_MS : false,
  });
}

// ── Mutations ───────────────────────────────────────────────────────────

export function useCreateKnowledgeBase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { name: string; config: KnowledgeBaseConfig }) =>
      request<KnowledgeBase>('', {
        method: 'POST',
        json: { name: vars.name, config: vars.config },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.kbList }),
  });
}

/** Patch a base's config. Server marks already-extracted files out of sync. */
export function useUpdateKnowledgeBaseConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { kbId: string; config: KnowledgeBaseConfig }) =>
      request<KnowledgeBase>(`/${vars.kbId}`, {
        method: 'PATCH',
        json: { config: vars.config },
      }),
    onSuccess: (_data, { kbId }) => {
      qc.invalidateQueries({ queryKey: keys.kb(kbId) });
      qc.invalidateQueries({ queryKey: keys.kbList });
      // File statuses may have flipped to out_of_sync.
      qc.invalidateQueries({ queryKey: keys.nodes(kbId) });
    },
  });
}

export function useCreateFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { kbId: string; parentId: string | null; name: string }) =>
      request<FileNode>(`/${vars.kbId}/folders`, {
        method: 'POST',
        json: { parentId: vars.parentId, name: vars.name },
      }),
    onSuccess: (_data, { kbId }) =>
      qc.invalidateQueries({ queryKey: keys.nodes(kbId) }),
  });
}

export function useUploadFiles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { kbId: string; parentId: string | null; files: File[] }) => {
      const form = new FormData();
      for (const f of vars.files) form.append('files', f);
      const q = vars.parentId
        ? `?parent=${encodeURIComponent(vars.parentId)}`
        : '';
      return request<FileNode[]>(`/${vars.kbId}/files${q}`, {
        method: 'POST',
        body: form,
      });
    },
    onSuccess: (_data, { kbId }) => {
      qc.invalidateQueries({ queryKey: keys.nodes(kbId) });
      qc.invalidateQueries({ queryKey: keys.kb(kbId) });
      qc.invalidateQueries({ queryKey: keys.kbList });
    },
  });
}

export function useDeleteNode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { kbId: string; nodeId: string }) =>
      request<void>(`/${vars.kbId}/nodes/${vars.nodeId}`, { method: 'DELETE' }),
    onSuccess: (_data, { kbId }) => {
      qc.invalidateQueries({ queryKey: keys.nodes(kbId) });
      qc.invalidateQueries({ queryKey: keys.kb(kbId) });
      qc.invalidateQueries({ queryKey: keys.kbList });
    },
  });
}

export function useResyncNode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { kbId: string; nodeId: string }) =>
      request<FileNode>(`/${vars.kbId}/files/${vars.nodeId}/resync`, {
        method: 'POST',
      }),
    onSuccess: (_data, { kbId, nodeId }) => {
      qc.invalidateQueries({ queryKey: keys.nodes(kbId) });
      qc.invalidateQueries({ queryKey: keys.file(kbId, nodeId) });
    },
  });
}
