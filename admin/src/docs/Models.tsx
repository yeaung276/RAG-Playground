import { Link } from 'react-router-dom';
import {
  CAPABILITY_LABELS,
  SCHEMA_CAPABILITIES,
  type ApiSchema,
  type Capability,
} from '../api/models';
import { C, H2, Note, P, Table } from './prose';

const CAPABILITY_NOTES: Record<Capability, string> = {
  'bi-encoder': 'Encodes text into a vector. Indexes knowledge and embeds queries.',
  'cross-encoder': 'Scores a query against each candidate chunk, to reorder retrieval results.',
  decoder: 'Generates text. Used by agents to answer and to call tools.',
};

const SCHEMA_NOTES: Record<ApiSchema, { routes: string; note: string }> = {
  openai: {
    routes: '/embeddings, /chat/completions',
    note: 'The OpenAI dialect — also spoken by vLLM, Azure OpenAI, Together and most gateways.',
  },
  tei: {
    routes: '/embed, /rerank',
    note: "Hugging Face Text Embeddings Inference. Its own request shape, not OpenAI's.",
  },
  cohere: {
    routes: '/rerank',
    note: 'The Cohere rerank body, copied by Jina, Infinity and vLLM. There is no OpenAI rerank route, so cross-encoders use this.',
  },
  gemini: {
    routes: '/interactions, /models/{name}:embedContent',
    note: 'The Gemini-native dialect on generativelanguage.googleapis.com. The key goes on the URL as ?key=, and generation settings live under generation_config.',
  },
};

const FIELDS: [string, string][] = [
  ['provider', 'Who serves the endpoint. Free text — openai, together, self-hosted.'],
  ['schema', 'The request dialect the endpoint speaks. Fixed once the model is created.'],
  ['baseUrl', 'Origin the request goes to, without the route — https://api.openai.com/v1.'],
  ['apiKey', 'Sent as the bearer token. Optional for endpoints on your own network.'],
  ['name', 'The model id passed in the request body, exactly as the provider expects it.'],
  ['capability', 'What the model is for. Fixed once the model is created.'],
];

export default function Models() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        A model is one endpoint you own: a base URL, the request dialect it speaks, the model id to
        ask for, and an optional API key. Register it once on the{' '}
        <Link to="/models" className="font-medium text-indigo-600 hover:text-indigo-700">
          Models
        </Link>{' '}
        page and it becomes selectable wherever a model is needed — knowledge indexing,
        reranking, and agents.
      </P>

      <H2 id="fields">Fields</H2>
      <Table
        head={['Field', 'What it means']}
        rows={FIELDS.map(([field, description]) => [
          <span className="whitespace-nowrap font-mono text-[13px] text-slate-800">{field}</span>,
          description,
        ])}
      />

      <H2 id="capabilities">Capabilities</H2>
      <P>
        Capability is what the model does, named after the architecture rather than the product
        word for it.
      </P>
      <Table
        head={['Capability', 'Shown as', 'What it does']}
        rows={(Object.keys(CAPABILITY_LABELS) as Capability[]).map((capability) => [
          <span className="whitespace-nowrap font-mono text-[13px] text-slate-800">
            {capability}
          </span>,
          <span className="whitespace-nowrap">{CAPABILITY_LABELS[capability]}</span>,
          CAPABILITY_NOTES[capability],
        ])}
      />

      <H2 id="schemas">API schemas</H2>
      <P>
        Schema and capability are not independent — an endpoint's dialect decides what it can
        serve. The form only offers valid pairs and the server rejects the rest.
      </P>
      <Table
        head={['Schema', 'Serves', 'Routes', 'Notes']}
        rows={(Object.keys(SCHEMA_CAPABILITIES) as ApiSchema[]).map((schema) => [
          <span className="whitespace-nowrap font-mono text-[13px] text-slate-800">{schema}</span>,
          <span className="whitespace-nowrap">
            {SCHEMA_CAPABILITIES[schema].map((c) => CAPABILITY_LABELS[c]).join(', ')}
          </span>,
          <span className="whitespace-nowrap font-mono text-[13px] text-slate-500">
            {SCHEMA_NOTES[schema].routes}
          </span>,
          SCHEMA_NOTES[schema].note,
        ])}
      />

      <H2 id="api-keys">API keys</H2>
      <P>
        The key is sealed with a random per-model data key, which is itself sealed with the
        key-encryption key mounted as <C>MODEL_KEK</C> on the backend, so the database never holds
        a usable secret. It is never returned to this console — a model only reports whether a key
        is set.
      </P>
      <Note title="Editing a key">
        Leave the key field blank to keep the stored key; clear it to remove the key entirely.
        Schema and capability cannot be changed after creation — register a second model instead.
      </Note>
    </>
  );
}
