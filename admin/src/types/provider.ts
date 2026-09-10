export type ProviderApi = 'openai' | 'anthropic' | 'openai-compatible';

export type Provider = {
  id: string;
  name: string;
  api: ProviderApi;
  baseUrl: string;
  apiKey: string;
  models: string[];
  enabled: boolean;
};

export const PROVIDER_APIS: { id: ProviderApi; label: string }[] = [
  { id: 'openai', label: 'OpenAI' },
  { id: 'anthropic', label: 'Anthropic' },
  { id: 'openai-compatible', label: 'OpenAI-compatible' },
];

export const apiLabel = (api: ProviderApi) =>
  PROVIDER_APIS.find((a) => a.id === api)?.label ?? api;
