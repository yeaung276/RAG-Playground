import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { requestAt } from './client';

const BASE = '/api/admin/models';

export type Capability = 'bi-encoder' | 'cross-encoder' | 'decoder';
export type ApiSchema = 'openai' | 'tei' | 'cohere' | 'gemini';

/** Capabilities each API schema can serve; mirrors VALID_PAIRS on the server. */
export const SCHEMA_CAPABILITIES: Record<ApiSchema, Capability[]> = {
  openai: ['bi-encoder', 'decoder'],
  tei: ['bi-encoder', 'cross-encoder'],
  cohere: ['cross-encoder'],
  gemini: ['bi-encoder', 'decoder'],
};

export const CAPABILITY_LABELS: Record<Capability, string> = {
  'bi-encoder': 'Embedding',
  'cross-encoder': 'Rerank',
  decoder: 'Chat',
};

export interface Model {
  id: string;
  provider: string;
  schema: ApiSchema;
  baseUrl: string;
  hasApiKey: boolean;
  name: string;
  capability: Capability;
  createdAt: string;
}

export interface ModelPage {
  items: Model[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ModelInput {
  provider: string;
  schema: ApiSchema;
  baseUrl: string;
  apiKey: string | null;
  name: string;
  capability: Capability;
}

const keys = {
  list: (page: number, capability: Capability | 'all') =>
    ['models', page, capability] as const,
};

export function useModels(page: number, capability: Capability | 'all', pageSize = 20) {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  if (capability !== 'all') params.set('capability', capability);
  return useQuery({
    queryKey: keys.list(page, capability),
    queryFn: () => requestAt<ModelPage>(`${BASE}?${params}`),
  });
}

export function useCreateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ModelInput) =>
      requestAt<Model>(BASE, { method: 'POST', json: input }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}

/** Patch fields on an existing model. Schema and capability are fixed at creation. */
export type ModelPatch = Partial<Pick<ModelInput, 'provider' | 'baseUrl' | 'apiKey' | 'name'>>;

export function useUpdateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; patch: ModelPatch }) =>
      requestAt<Model>(`${BASE}/${vars.id}`, { method: 'PATCH', json: vars.patch }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}

export function useDeleteModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => requestAt<void>(`${BASE}/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['models'] }),
  });
}
