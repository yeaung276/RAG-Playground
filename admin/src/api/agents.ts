import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { requestAt } from './client';

const BASE = '/api/admin/agents';

export type HandoffMode = 'none' | 'auto' | 'manual';
export type AuthKind = 'none' | 'bearer' | 'header' | 'basic';

export interface KV {
  id?: string;
  key: string;
  value: string;
}

export interface Param {
  id?: string;
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export interface Tool {
  id?: string;
  name: string;
  description: string;
  enabled: boolean;
  method: string;
  url: string;
  headers: KV[];
  query: KV[];
  body: string;
  auth: AuthKind;
  authHeader: string;
  authUser: string;
  authPass: string;
  timeoutMs: number;
  params: Param[];
  /** The token itself never comes back — only whether one is stored. */
  hasAuthToken: boolean;
}

/** A tool on the way out: omit `authToken` to keep the stored one. */
export type ToolInput = Omit<Tool, 'hasAuthToken'> & { authToken?: string };

export interface HandoffTarget {
  id?: string;
  agentId: string;
  description: string;
}

export interface Handoff {
  mode: HandoffMode;
  targets: HandoffTarget[];
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  instruction: string;
  modelId: string | null;
  temperature: number;
  knowledgeId: string | null;
  maxStep: number;
  tools: Tool[];
  handoff: Handoff;
  isEntrypoint: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Roster row: counts instead of the tool and handoff documents. */
export interface AgentSummary {
  id: string;
  name: string;
  description: string;
  isEntrypoint: boolean;
  handoffMode: HandoffMode;
  enabledToolCount: number;
  handoffCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface AgentInput {
  name: string;
  description?: string;
  instruction?: string;
  modelId?: string | null;
  temperature?: number;
  knowledgeId?: string | null;
  maxStep?: number;
  tools?: ToolInput[];
  handoff?: Handoff;
}

const keys = {
  list: ['agents'] as const,
  detail: (id: string) => ['agents', id] as const,
};

export function useAgents() {
  return useQuery({
    queryKey: keys.list,
    queryFn: () => requestAt<AgentSummary[]>(BASE),
  });
}

/** The full agent, including its tools and handoff targets. */
export function useAgent(id: string) {
  return useQuery({
    queryKey: keys.detail(id),
    queryFn: () => requestAt<Agent>(`${BASE}/${id}`),
    enabled: !!id,
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AgentInput) => requestAt<Agent>(BASE, { method: 'POST', json: input }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list }),
  });
}

export interface SentRequest {
  method: string;
  url: string;
  headers: Record<string, string>;
  query: Record<string, string>;
  body: string | null;
}

export interface ToolTestResult {
  request: SentRequest;
  status: number | null;
  elapsedMs: number;
  body: string;
  error: string | null;
}

/**
 * Runs the tool as currently edited — it need not be saved. Omitting
 * `authToken` falls back to the token stored under that tool name.
 */
export function useTestTool() {
  return useMutation({
    mutationFn: (vars: { agentId: string; tool: ToolInput; params: Record<string, string> }) =>
      requestAt<ToolTestResult>(`${BASE}/${vars.agentId}/tools/test`, {
        method: 'POST',
        json: { tool: vars.tool, params: vars.params },
      }),
  });
}

/** Everything but the name, which is fixed at creation. */
export type AgentPatch = Omit<AgentInput, 'name'>;

export function useUpdateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: string; patch: AgentPatch }) =>
      requestAt<Agent>(`${BASE}/${vars.id}`, { method: 'PATCH', json: vars.patch }),
    onSuccess: (agent) => {
      qc.invalidateQueries({ queryKey: keys.list });
      qc.invalidateQueries({ queryKey: keys.detail(agent.id) });
    },
  });
}

/** Promotes one agent and demotes the previous entrypoint server-side. */
export function useSetEntrypoint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => requestAt<Agent>(`${BASE}/${id}/entrypoint`, { method: 'PUT' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list }),
  });
}

export function useDeleteAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => requestAt<void>(`${BASE}/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.list }),
  });
}
