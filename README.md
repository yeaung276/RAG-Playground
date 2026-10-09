<div align="center">

# RAG Playground

**Build agents that answer from your documents — and prove they do.**

A self-hosted platform for retrieval-augmented agents: register models, index documents,
configure multi-agent assistants with tools and handoffs, measure retrieval quality with
generated datasets and experiments, and ship it all as an embeddable chat widget.

[![CI](https://github.com/yeaung276/RAG-Playground/actions/workflows/pytest.yml/badge.svg)](https://github.com/yeaung276/RAG-Playground/actions/workflows/pytest.yml)
![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Qdrant](https://img.shields.io/badge/Qdrant-vector%20store-DC244C)

<img src="admin/src/docs/assets/tracing-and-testing-agent.png" alt="Testing an agent with a live trace of every message and tool call" width="900" />

</div>

---

## Table of contents

- [Why RAG Playground](#why-rag-playground)
- [Features](#features)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Getting started](#getting-started)
- [Running with Docker](#running-with-docker)
- [Configuration](#configuration)
- [Embedding the chat widget](#embedding-the-chat-widget)
- [How it works](#how-it-works)
- [Observability](#observability)
- [API reference](#api-reference)
- [CLI](#cli)
- [Project structure](#project-structure)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Why RAG Playground

Most RAG stacks make it easy to wire up retrieval and hard to tell whether it works. RAG
Playground puts the whole loop in one console:

1. **Build** — agents with prompts, tools, knowledge and handoffs, configured in the UI.
2. **Ground** — knowledge bases with configurable chunking, hybrid search, reranking and HyDE.
3. **Measure** — synthetic question/answer datasets and experiments that score every change.
4. **Ship** — a two-tag chat widget, with live supervision and takeover for your team.

---

## Features

### 🤖 Agents

- Configure each agent's model, system prompt, temperature and step limit.
- **HTTP tools** with `{{placeholder}}` parameters, bearer / header / basic auth, and a
  test button that makes the real request.
- **Multi-agent handoffs** — automatic (every agent is a target) or manual with your own
  routing rules; one agent is the **entrypoint**.
- Attach a knowledge base and the agent gets a `search_knowledge` tool.
- **Test the whole roster live** with a streaming trace of every message, tool call,
  result, timing and reasoning token.

### 📚 Knowledge bases

- Folder tree of documents; text is read as-is, **PDFs and images are OCR'd** with
  Typhoon OCR.
- **Small-to-big chunking** — `fix-sized`, `recursive` or `semantic` parent chunks,
  with small child chunks embedded for search.
- **Hybrid search** — BM25 (sparse) and any number of dense embedding models, fused
  with reciprocal rank fusion.
- **Reranking** with a cross-encoder or a late-interaction (per-token) model.
- **HyDE** — search with a model-written hypothetical answer instead of the raw query.

### 🧪 Evaluation

- **Generate datasets** from a zip of documents: question/answer pairs with a chosen
  mix of `simple`, `reasoning`, `multi_context` and `conditional` questions, plus your
  own labels.
- **Run experiments** against a fresh or existing knowledge base with any retrieval
  setup.
- **Metrics**: context precision, context recall, hit rate and MRR, broken down by
  category and label and compared with your best run so far.
- **Error analysis** — every retrieved chunk with the golden sentences it caught
  highlighted.

### 💬 Live chat

- Embeddable **chat widget** served as a single `widget.js`, streaming replies over
  Server-Sent Events.
- **Control Panel** — live sessions ordered by attention priority; **intercept** (take
  over) or **audit** (watch) any conversation.
- Like / dislike feedback on replies.

### ⚙️ Platform

- **Model registry** for OpenAI-compatible, Hugging Face TEI, Cohere and Gemini
  endpoints — chat, embeddings, cross-encoders and late-interaction models.
- API keys and tool credentials **encrypted at rest** (envelope encryption).
- Admin console with signed-cookie auth, landing page and built-in docs.
- Prometheus metrics for background jobs, OCR, retrieval, model endpoints, agents and
  live chat, with a ready-made Grafana dashboard — see [Observability](#observability).

---

## Screenshots

| | |
|---|---|
| <img src="admin/src/docs/assets/agents.png" alt="Agents" /> | <img src="admin/src/docs/assets/knowledge-base-config.png" alt="Knowledge base configuration" /> |
| **Agents** — roster, entrypoint and per-agent settings | **Knowledge base** — chunking, indexing and retrieval in one form |
| <img src="admin/src/docs/assets/knowledge-base.png" alt="Knowledge base files" /> | <img src="admin/src/docs/assets/dataset.png" alt="Dataset" /> |
| **Files** — folder tree, uploads and per-file status | **Datasets** — generated pairs with category and label composition |
| <img src="admin/src/docs/assets/experiment-result.png" alt="Experiment result" /> | <img src="admin/src/docs/assets/experiment-comparison.png" alt="Experiment comparison" /> |
| **Experiments** — scores against the best run, by category and label | **Trends** — every metric tracked across runs |
| <img src="admin/src/docs/assets/experiment-error-analysis.png" alt="Error analysis" /> | <img src="admin/src/docs/assets/tracing-and-testing-agent.png" alt="Agent test run" /> |
| **Error analysis** — golden sentences highlighted in retrieved chunks | **Test runs** — live trace of messages and tool calls |

---

## Architecture

```
 Visitor's page (widget.js)          Admin console (/#/…)
   │  POST /api/control                │  /api/admin/*  (signed-cookie auth)
   │  POST /api/messages               │
   ▼                                   ▼
 ┌───────────────────────────────────────────────────────────────┐
 │ FastAPI (app/)                                                │
 │  routers → services → background jobs                         │
 │  LangGraph agent runtime · retrieval · evaluation             │
 └───────────────────────────────────────────────────────────────┘
   │              │                 │                    │
   ▼              ▼                 ▼                    ▼
 PostgreSQL     Qdrant           Local storage        Model endpoints
 (app data +    (one collection  (uploads, datasets,  (registered models,
  agent state)   per knowledge    experiment results)  Typhoon OCR)
                 base)
```

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, async SQLAlchemy 2.0 + asyncpg, Alembic, uv |
| Agents | LangChain + LangGraph, with a Postgres checkpointer |
| Retrieval | Qdrant (dense, sparse and multi-vector), LangChain text splitters |
| OCR | Typhoon OCR over an OpenAI-compatible `/chat/completions` endpoint |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query & Form, Radix UI |
| Widget | Second entry of the same Vite build, mounted in a shadow root |
| Observability | Prometheus metrics via `prometheus-fastapi-instrumentator` |

The FastAPI app serves the built frontend from `admin/dist/`:

- `/` — landing page
- `/#/control`, `/#/agents`, … — admin console (redirects to `/#/login` when signed out)
- `/#/docs` — in-app documentation
- `/widget.js` — the embeddable chat widget

---

## Getting started

### Prerequisites

- [Python 3.12+](https://www.python.org/) and [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Node.js 20+](https://nodejs.org/) and [Yarn](https://yarnpkg.com/)
- [Docker](https://www.docker.com/) (for PostgreSQL, Qdrant and Typhoon OCR)

### 1. Clone and install

```bash
git clone https://github.com/yeaung276/RAG-Playground.git
cd RAG-Playground
uv sync
```

### 2. Configure

```bash
cp .env.example .env
```

At minimum, set `MODEL_KEK` — the key that encrypts stored API keys:

```bash
python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"
```

See [Configuration](#configuration) for everything else.

### 3. Start the backing services

```bash
docker compose up -d db qdrant typhoon
```

`typhoon` is only needed to OCR PDFs and images — skip it and point `TYPHOON_BASE_URL` at
a hosted Typhoon OCR endpoint if you prefer. Make sure `DATABASE_URL`, `QDRANT_URL` and
`TYPHOON_BASE_URL` in `.env` point at these services.

### 4. Set up the database

```bash
uv run python main.py migrate upgrade head
```

### 5. Run

```bash
uv run python main.py dev
```

This installs the frontend dependencies, rebuilds the console and `widget.js` on every
change (`vite build --watch`), and runs the API with `uvicorn --reload`. Open
`http://localhost:8000/` for the landing page, then **Open console** to sign in.

### 6. First steps

1. **Models** — register a chat model (decoder) and an embedding model (bi-encoder).
2. **Knowledge** — create a base and upload a few documents.
3. **Agents** — add an agent, pick its model, attach the knowledge base, and press
   **Test**.
4. **Evaluation** — generate a dataset from a zip of documents, then run an experiment.

---

## Running with Docker

```bash
docker compose up --build
```

The compose file runs four services:

| Service | What it is |
|---|---|
| `app` | This application — API, admin console and widget |
| `db` | PostgreSQL |
| `qdrant` | Qdrant vector store |
| `typhoon` | Typhoon OCR model server |

The image is built from the [`Dockerfile`](Dockerfile) in two stages: Node 20 builds the
admin console and `widget.js` into `admin/dist`, then a Python 3.12 slim image installs
the locked dependencies with uv and runs `uvicorn app.app:app` on port `8000`. Configure
the app with the variables from [Configuration](#configuration).

The runtime image contains only `app/` and the built frontend, so run migrations from a
checkout, pointed at the same database:

```bash
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/<db> \
  uv run python main.py migrate upgrade head
```

---

## Configuration

Settings are read from the environment and from `.env` (see
[`app/config.py`](app/config.py) and [`.env.example`](.env.example)).

### Core

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `info` | `debug`, `info`, `warning` or `error` |
| `AGENT_NAME` | `Assistant` | Sender name on replies an admin sends into an intercepted chat |

### Database & vector store

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/chat_gateway` | Async SQLAlchemy URL; also used by the LangGraph checkpointer |
| `DB_ECHO` | `false` | Log every SQL statement |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant REST endpoint |
| `QDRANT_API_KEY` | — | Qdrant API key (optional when self-hosted) |

### Sessions & admin auth

| Variable | Default | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS allowlist — add every site that embeds the widget |
| `SESSION_COOKIE_NAME` | `chat_session` | Chat session cookie name |
| `SESSION_COOKIE_SECURE` | `true` | Send the session cookie over HTTPS only |
| `SESSION_COOKIE_SAMESITE` | `none` | SameSite policy of the session cookie |
| `SESSION_TIMEOUT_MINUTES` | `30` | Idle time before a chat session expires |
| `ADMIN_SECRET_KEY` | `change-me-in-production` | Signs the admin session cookie — **change this in production** |
| `ADMIN_COOKIE_NAME` | `admin_session` | Admin session cookie name |
| `ADMIN_SESSION_HOURS` | `1` | Admin session lifetime |

### Storage & secrets

| Variable | Default | Description |
|---|---|---|
| `STORAGE_PATH` | `.knowledge/storage` | Directory for uploaded files, dataset archives and experiment results |
| `MODEL_KEK` | — | Key-encryption key for model API keys and tool credentials: 32 random bytes, base64-encoded. **Required** to store any secret |

### OCR

| Variable | Default | Description |
|---|---|---|
| `TYPHOON_BASE_URL` | — | Typhoon OCR base URL (OpenAI-compatible `/chat/completions`) |
| `TYPHOON_OCR_API_KEY` | — | Typhoon OCR API key |
| `TYPHOON_OCR_MODEL` | `typhoon-ai/typhoon-ocr-7b` | OCR model name |

### Model endpoint limits

Requests to registered models are rate-limited and batched per process.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_EMBEDDING_RPS` | `10` | Requests per second to OpenAI-compatible `/embeddings` |
| `TEI_EMBEDDING_RPS` · `TEI_EMBEDDING_MAX_BATCH` | `10` · `32` | TEI `/embed` rate and batch size |
| `TEI_RERANKER_RPS` · `TEI_RERANKER_MAX_BATCH` | `10` · `32` | TEI `/rerank` rate and batch size |
| `TEI_LATE_INTERACTION_RPS` · `TEI_LATE_INTERACTION_MAX_BATCH` | `10` · `8` | Late-interaction rate and batch size |

### Fallback endpoints

Models are normally configured in the console. These are used only when a registered
model has no base URL or API key of its own.

| Variable | Used by |
|---|---|
| `OPENAI_BASE_URL` · `OPENAI_API_KEY` | OpenAI-compatible embedding models |
| `TEI_EMBEDDING_BASE_URL` · `TEI_EMBEDDING_API_KEY` | TEI embedding models |
| `TEI_RERANKER_BASE_URL` · `TEI_RERANKER_API_KEY` | TEI cross-encoders |
| `TEI_LATE_INTERACTION_BASE_URL` · `TEI_LATE_INTERACTION_API_KEY` | TEI late-interaction models |

---

## Embedding the chat widget

Add two script tags to any page:

```html
<script type="module" src="https://your-host/widget.js"></script>
<script type="module">
  widgets.createChat({
    agentName: 'Assistant',
    welcomeMessage: 'Hi! Ask me anything.',
    position: 'bottom-right',
    waveColor: '#6366f1',
  });
</script>
```

Every option is optional — `createChat()` with no arguments works. Remember to add the
embedding site to `ALLOWED_ORIGINS`.

| Option | Default | Description |
|---|---|---|
| `backendUrl` | the directory `widget.js` was loaded from | Base URL for API calls |
| `position` | `'bottom-right'` | `'bottom-right'`, `'bottom-left'`, `'top-right'` or `'top-left'` |
| `offsetX` / `offsetY` | `20` / `20` | Distance from that corner, in px |
| `waveColor` | `'#6366f1'` | Chat head colour and its pulsing rings |
| `innerSize` / `outerSize` | `56` / `80` | Chat head diameter and its wave area, in px (`outerSize` must be larger) |
| `iconUrl` | — | Chat head image; a plain circle in `waveColor` when unset |
| `panelWidth` / `panelHeight` | `384` / `600` | Open panel size, in px |
| `panelBg` | `'#ffffff'` | Panel background (any CSS colour) |
| `agentName` | `'Assistant'` | Name shown in the panel header and on replies |
| `welcomeMessage` | `'This is the widget panel.'` | Greeting shown as the first bubble; never sent to the backend |

**How `backendUrl` is resolved.** By default the widget calls the API in the directory it
was loaded from (`new URL(".", import.meta.url)`), not just the origin. A script served at
`https://example.com/chat/widget.js` talks to `https://example.com/chat/api/...`, so the
gateway works behind a reverse proxy on a sub-path with no configuration.

---

## How it works

### Ingestion

Uploading a file queues a background job:

1. **Extract** — text files are read directly; PDFs and images are rendered and OCR'd
   page by page with Typhoon OCR.
2. **Chunk** — documents are split into **parent** chunks by the base's method
   (`fix-sized`, `recursive` or `semantic`), and each parent into **child** chunks of 512
   characters with 40 characters of overlap.
3. **Index** — every child is embedded once per index and stored as one Qdrant point
   carrying a named vector per index (`bm25` sparse, or a dense vector named after its
   model). Parents are stored in Postgres (`knowledge_chunks`). With a late-interaction
   reranker, per-token vectors of every parent are stored as well.

Each knowledge base is its own Qdrant collection. Its index types fix the vector layout,
so changing them recreates the collection and marks indexed files **out of sync**.

### Retrieval

1. Optionally, **HyDE** asks a chat model for a hypothetical answer to search with.
2. The text is embedded once per requested index; each index prefetches its best child
   matches (`prefetchLimit`).
3. Multiple indexes are fused with **reciprocal rank fusion**, and children are collapsed
   to distinct parents server-side (`rerankPool` of them).
4. Optionally, the parents (or the matched children) are **reranked** against the
   original query.
5. The best `topK` parents are returned.

### Agents

Every saved agent becomes a node in a LangGraph graph, starting at the **entrypoint**.
Each agent gets its HTTP tools, a `search_knowledge` tool when a knowledge base is
attached, and one `transfer_to_<name>` tool per handoff target. A transfer is always
the only call on its turn, and the step limit ends a run after that many model calls.
Conversation state is checkpointed in Postgres, keyed by the chat session.

### Evaluation

- **Datasets** — a chat model reads each file in a zip archive and writes the requested
  number of question/answer pairs, each with a category, labels, the source file and the
  **golden text** the answer comes from.
- **Experiments** — optionally index the dataset's files into a new knowledge base, then
  retrieve for every question and score the result. A retrieved chunk is **relevant**
  when it comes from the pair's source file and contains at least one golden sentence.

| Metric | Measures |
|---|---|
| Context precision | Share of retrieved chunks that are relevant |
| Context recall | Share of golden sentences found in the retrieved chunks |
| Hit rate | Whether any retrieved chunk is relevant |
| MRR | 1 / rank of the first relevant chunk |

### Live chat

The widget opens a per-session Server-Sent Events stream at `POST /api/control`, which
sets an HttpOnly session cookie. Messages are sent with `POST /api/messages`; the reply
streams back on that response and is also broadcast on the control stream. When an admin
**intercepts** a session, no reply is generated and the admin's messages reach the
visitor through the control stream instead.

---

## Observability

The app exposes Prometheus metrics at `/metrics`: default HTTP metrics (request counts,
latency, requests in progress) plus the application metrics below. Metrics are kept per
process, so sum across instances in your queries.

| Area | Metric | Type | Labels | Measures |
|---|---|---|---|---|
| Generation | `generation_requests_total` | counter | `status` | Full agent replies, by outcome |
| | `generation_duration_seconds` | histogram | — | Time for one full agent reply, including tools and retrieval |
| File processing | `file_processing_total` | counter | `status` | Files processed: `completed`, `failed`, `unsupported` |
| | `file_processing_duration_seconds` | histogram | — | Time to extract and index one file |
| | `file_processing_in_progress` | gauge | — | Files being processed right now |
| OCR | `ocr_pages_total` | counter | `status` | Pages sent to OCR: `completed`, `failed` |
| | `ocr_page_duration_seconds` | histogram | — | Time per OCR page, including retries |
| | `ocr_requests_in_flight` | gauge | — | OCR concurrency slots in use (8 per process) |
| Indexing | `indexed_chunks_total` | counter | `level` | Chunks written: `parent`, `child` |
| | `qdrant_upsert_duration_seconds` | histogram | — | Time per Qdrant upsert batch |
| Retrieval | `retrieval_duration_seconds` | histogram | — | End-to-end time of one knowledge search |
| | `retrieval_stage_duration_seconds` | histogram | `stage` | Time per stage: `hyde`, `embed`, `search`, `hydrate`, `rerank` |
| | `retrieval_empty_total` | counter | — | Searches that returned nothing |
| Model endpoints | `model_request_duration_seconds` | histogram | `model`, `operation` | Time per request to a registered model (`embed`, `rerank`, `late_interaction`) |
| | `model_request_errors_total` | counter | `model`, `operation` | Failed model requests |
| | `model_batch_size` | histogram | `model`, `operation` | Texts per model request |
| | `model_rate_limit_wait_seconds` | histogram | `model`, `operation` | Time waiting on the per-process rate limiter |
| | `http_retries_total` | counter | `call` | Outbound calls retried after a transient failure |
| Agents | `agent_model_call_duration_seconds` | histogram | `agent` | Time per model call |
| | `agent_tokens_total` | counter | `agent`, `kind` | Tokens used: `input`, `output` |
| | `agent_tool_calls_total` | counter | `agent`, `tool`, `status` | Tool calls, by outcome |
| | `agent_tool_duration_seconds` | histogram | `tool` | Time per tool call |
| | `agent_handoffs_total` | counter | `from_agent`, `to_agent` | Conversations handed between agents |
| | `agent_step_limit_total` | counter | `agent` | Runs ended by the step limit |
| Datasets | `dataset_generation_total` | counter | `status` | Generation runs: `ready`, `failed` |
| | `dataset_generation_duration_seconds` | histogram | — | Time to generate one dataset |
| | `dataset_pairs_generated_total` | counter | — | Question/answer pairs written |
| Experiments | `experiment_runs_total` | counter | `status` | Runs: `success`, `failed` |
| | `experiment_stage_duration_seconds` | histogram | `stage` | Time spent `importing` and `scoring` |
| Live chat | `sse_connections` | gauge | `stream` | Open event streams: `control`, `admin_notifications`, `admin_intercept`, `admin_audit` |
| | `chat_session_events_total` | counter | `event` | Sessions `created`, `reconnected`, `disconnected`, `expired` |
| | `chat_takeovers_total` | counter | `action` | Admin take-overs: `intercept`, `release` |
| | `realtime_events_dropped_total` | counter | `reason` | Events that never reached a subscriber: `malformed`, `slow_subscriber` |
| | `realtime_reconnects_total` | counter | — | Reconnects of the realtime listener to Postgres |
| Quality & auth | `message_feedback_total` | counter | `value` | Votes on replies: `like`, `dislike`, `cleared` |
| | `admin_logins_total` | counter | `status` | Admin logins: `success`, `failure` |

`model` is the registered model's name and `agent` the agent's name, so label values stay
bounded by what is configured in the console.

### Grafana dashboard

[`.grafana/dashboards/app-dashboard.json`](.grafana/dashboards/app-dashboard.json) charts
all of the above, in rows for HTTP traffic, generation, background jobs, OCR and
indexing, retrieval, model endpoints, agents, live chat, and quality and auth. To use it:

1. Scrape the app's `/metrics` with Prometheus under the job name `chat-gateway` (the
   dashboard's `instance` filter reads that job).
2. Add that Prometheus to Grafana as a data source with the UID `Prometheus`.
3. Import the dashboard JSON.

---

## API reference

All request and response bodies are camelCase JSON. Streaming endpoints return
`text/event-stream` with one JSON frame per `data:` line.

### Public

| Endpoint | Description |
|---|---|
| `POST /api/control` | Open the session's event stream and set the session cookie. `?new=true` forces a fresh session. Emits `message.created` and `feedback.updated` |
| `POST /api/messages` | Send `{ sender, content, imageBase64?, imageMimeType? }` and stream the agent's reply. `401` without a session cookie |
| `GET /api/messages` | The session's newest 20 messages, oldest first |
| `POST /api/messages/{id}/feedback` | `{ "value": "like" \| "dislike" \| null }` |
| `GET /health` | `{ "status": "ok" }` |
| `GET /metrics` | Prometheus metrics |

Reply stream frames:

| `type` | Payload | Meaning |
|---|---|---|
| `thinking` | `agent`, `delta` | Reasoning tokens, when the model emits them |
| `token` | `agent`, `delta` | The next slice of the reply |
| `tool_call` | `name` | A tool the agent started calling |
| `tool_result` | `agent`, `name`, `args`, `content`, `status`, `elapsedMs` | A tool's result |
| `message` | `agent`, `role`, `content`, `thinking`, `usage` | A finished model message |
| `error` | `message` | The run failed |
| `done` | `id` | End of the reply; `id` is the persisted message (absent when intercepted) |

### Admin (`/api/admin`)

Every route except `login`, `logout` and `me` requires the admin session cookie. List
endpoints take `page` and `pageSize`.

| Area | Endpoints |
|---|---|
| Auth | `POST /login` · `POST /logout` · `GET /me` |
| Chats | `GET /chats/current` · `GET /chats/history` · `GET /chats/{sessionId}/messages` · `POST /chats/{sessionId}/messages` · `POST /chats/{sessionId}/intercept` (event stream) |
| Notifications | `GET /notifications` (event stream) |
| Agents | `POST /agents` · `GET /agents` · `GET /agents/{id}` · `PATCH /agents/{id}` · `DELETE /agents/{id}` · `PUT /agents/{id}/entrypoint` · `POST /agents/{id}/tools/test` · `POST /agents/test` (event stream) |
| Models | `POST /models` · `GET /models?capability=` · `GET /models/{id}` · `PATCH /models/{id}` · `DELETE /models/{id}` |
| Knowledge bases | `POST /knowledge` · `GET /knowledge` · `GET /knowledge/{kbId}` |
| Files | `POST /knowledge/{kbId}/folders` · `POST /knowledge/{kbId}/files` (multipart) · `GET /knowledge/{kbId}/nodes?parent=` · `GET /knowledge/{kbId}/files/{nodeId}` · `GET /knowledge/{kbId}/files/{nodeId}/download` · `POST /knowledge/{kbId}/files/{nodeId}/resync` · `DELETE /knowledge/{kbId}/nodes/{nodeId}` |
| Datasets | `POST /datasets` (multipart: `payload` JSON + `archive` zip) · `GET /datasets` · `GET /datasets/{id}` · `GET /datasets/{id}/pairs` · `POST /datasets/{id}/retry` |
| Experiments | `POST /experiments` · `GET /experiments?datasetId=` · `GET /experiments/score_board?datasetId=` · `GET /experiments/{id}` · `GET /experiments/{id}/best` · `GET /experiments/{id}/result` · `POST /experiments/{id}/rerun` |

---

## CLI

Run as `uv run python main.py <command>`; add `-h` to any command for its options.

| Command | Description |
|---|---|
| `dev` | Run the API with `--reload` and watch-build the frontend |
| `migrate <alembic args>` | Forward to Alembic — `upgrade head`, `downgrade -1`, `revision --autogenerate -m "msg"`, `current`, `history` |

---

## Project structure

```
.
├── app/                    FastAPI backend
│   ├── routers/            HTTP routes — chat, control, admin/*
│   ├── services/           Business logic — agents, chat, dataset, knowledge, models, retrieval
│   ├── backgrounds/        Background jobs — file indexing, dataset generation, experiments
│   ├── models/             SQLAlchemy tables
│   ├── schemas/            Request / response models
│   ├── db/                 Postgres, Qdrant and LangGraph checkpointer clients
│   └── storage/            Blob storage for uploads and results
├── admin/                  Frontend — one Vite build
│   └── src/
│       ├── pages/          Admin console screens
│       ├── docs/           Landing page and in-app docs
│       └── widget/         Embeddable chat widget (→ widget.js)
├── migrations/             Alembic migrations
├── tests/                  Backend tests (pytest)
├── datasets/thai-treasury/ Thai treasury dataset — extracted documents (texts/) and question sets (eval/)
├── Dockerfile
├── docker-compose.yaml
└── main.py                 CLI entry point
```

### Data

- **PostgreSQL** — `admins`, `sessions`, `messages`, `agents`, `models`,
  `knowledge_bases`, `knowledge_nodes` (file tree), `knowledge_chunks` (parent chunks),
  `datasets`, `experiments`. The LangGraph checkpointer creates its own tables at
  startup.
- **Qdrant** — one collection per knowledge base, one point per child chunk (plus one per
  parent with a late-interaction reranker). Payload: `chunk_id`, `own_chunk_id`,
  `node_id`, `content`, `source`, `pages`, `parent`.
- **Storage** — original uploads, dataset archives and pairs, and experiment results
  under `STORAGE_PATH`.

---

## Development

```bash
# Backend tests (CI runs these on every pull request to main)
mkdir -p admin/dist
uv run pytest

# New migration after changing a model in app/models/
uv run python main.py migrate revision --autogenerate -m "describe the change"
uv run python main.py migrate upgrade head

# One-off production build of the frontend
yarn --cwd admin build
```

The frontend is always built, never served by a dev server — `main.py dev` rebuilds
`admin/dist/` on change and FastAPI serves it. New metrics go in
[`app/metrics.py`](app/metrics.py); add them to the [Observability](#observability) table
and the Grafana dashboard too.

---

## Contributing

Contributions are welcome.

1. Fork the repository and create a branch from `main`.
2. Make your change, with tests where it makes sense.
3. Run `uv run pytest` and make sure the frontend builds.
4. Open a pull request against `main` describing what changed and why.

For larger changes, open an issue first to discuss the approach.

---

## License

No license has been chosen for this project yet. Until a `LICENSE` file is added, all
rights are reserved by the authors.
