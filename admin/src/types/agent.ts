export type KV = { id: string; key: string; value: string };

export type Param = {
  id: string;
  name: string;
  type: 'string' | 'number' | 'boolean';
  required: boolean;
  description: string;
};

export type Tool = {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  url: string;
  headers: KV[];
  query: KV[];
  body: string;
  auth: 'none' | 'bearer' | 'header' | 'basic';
  authToken: string;
  authHeader: string;
  authUser: string;
  authPass: string;
  timeoutMs: number;
  params: Param[];
  hasAuthToken: boolean;
  saved: boolean;
};

export type HandoffMode = 'none' | 'auto' | 'manual';

export type Handoff = { id: string; targetId: string; description: string };

export type Agent = {
  id: string;
  name: string;
  description: string;
  instruction: string;
  modelId: string | null;
  temperature: number;
  knowledgeId: string | null;
  maxStep: number;
  isEntrypoint: boolean;
  handoffMode: HandoffMode;
  handoffs: Handoff[];
  tools: Tool[];
};

export const uid = () => Math.random().toString(36).slice(2, 8);
