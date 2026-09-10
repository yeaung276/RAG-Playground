# Chat Gateway

A chat gateway that answers messages with a streaming LLM agent, serves an embeddable
chat widget, and ships an admin console for live-chat supervision and knowledge-base
management (document upload + OCR + RAG indexing).

---

## Architecture

```
Browser (widget.js)     Admin console (/)
    │  POST /api/control     │  /api/admin/*
    │  POST /api/messages     │  (signed-cookie auth)
    ▼                         ▼
                        FastAPI (app/)
    │
    ├── /api/control            → per-session SSE stream (sets session cookie)
    ├── /api/messages           → send a message, stream the agent's reply
    ├── /api/messages/{id}/feedback → like / dislike a message
    ├── /api/admin/*            → admin console API (auth, chats, knowledge base)
    ├── /metrics                → Prometheus metrics
    ├── /health                 → health check
    ├── /dev                    → widget preview page (DEV only)
    └── /*                      → admin/dist: the console at /, widget.js, assets/
    │
    ▼
PostgreSQL  (sessions, messages, admins, knowledge base)
Qdrant      (child-chunk vectors, one collection per knowledge base)
```

- **Backend** — FastAPI + uv (Python 3.12+), async SQLAlchemy 2.0 + asyncpg
- **Admin console** — React + Vite + TailwindCSS, built to `admin/dist/`, served at `/`
- **Widget** — source in `admin/src/widget/`, a second entry of the same Vite build
  (`admin/src/embed.tsx` → `admin/dist/widget.js`), served at `/widget.js`
- **Database** — PostgreSQL; migrations via Alembic
- **Vector store** — Qdrant, one collection per knowledge base

---

## Components

### Backend (`app/`)

FastAPI app (`app.app:app`). Routers live in `app/routers/` (chat, control,
admin) and business logic in `app/services/` grouped by domain (`chat`, `admin`,
`knowledge`, `retrieval`, `realtime`).

Chat is **session-based**. The widget first opens an SSE stream at `POST /api/control`,
which creates or reconnects a session and sets an HttpOnly session cookie
(`SESSION_COOKIE_NAME`, default `chat_session`). Subsequent `POST /api/messages` calls
are authenticated by that cookie; the reply streams back token by token on that POST
response, and the finished message is persisted and pushed over the open control
stream as well. This lets an admin **intercept** a live session — when intercepted, no
generation runs, the POST answers with a bare `done` frame, and the admin's replies
reach the user through the control stream instead.

### Admin console (`admin/`)

React + TypeScript + Vite single-page app (TanStack Query, react-router `HashRouter`,
TailwindCSS, Radix UI). Served as static files at `/` (routes are hash-based, e.g.
`/#/control`); its API lives under `/api/admin/*` and is protected by a signed-cookie
session.

The chat widget shares this app: `admin/src/widget/` is a second Vite entry
(`admin/src/embed.tsx`) emitted as `widget.js` into the same `dist/`, so both are one
build sharing chunks under `assets/`. The widget mounts into a shadow root with its
own Tailwind sheet (`admin/src/widget/index.css`, scanning scoped to that folder).

Two areas:

- **Control Panel** (`/control`) — live list of chat sessions, ordered by attention
  priority, with a realtime feed. Open a session to view its transcript, and
  **intercept** (take over the conversation) or **audit** (watch live).
- **Knowledge Base** (`/knowledge`) — create knowledge bases, upload documents into a
  file tree, and configure indexing. Gated by the `ENABLE_KNOWLEDGE_BASE` feature flag
  (see [Feature Flags](#feature-flags)).

Admin users are created from the CLI (`main.py createadmin`) and stored in the
`admins` table (bcrypt-hashed passwords).

### Knowledge Base & RAG (`app/services/knowledge/`, `app/services/retrieval/`)

Documents uploaded through the admin console are processed by a background task:

1. **Extract** — PDFs and images are OCR'd via Typhoon OCR (OpenAI-compatible
   `/chat/completions`), one page → one document page.
2. **Chunk** — a two-level "small-to-big" parent/child split. The parent splitter is
   selectable (`fix-sized`, `recursive`, or `semantic`); child chunks are fixed
   (size 512, overlap 40).
3. **Index** — child chunks are embedded once per configured index and upserted as a
   single Qdrant point carrying one named vector per index; parents go to
   `knowledge_chunks` in Postgres.
4. **Retrieve** — the query is embedded against each requested index, Qdrant fuses the
   rankings with RRF and collapses children to distinct parents server-side
   (`query_points_groups` on `chunk_id`), then parents are loaded from Postgres.

A knowledge base's `indexTypes` lists which indexes to build; each entry is both the
index name and its Qdrant vector name:

| `indexTypes` entry | Kind | Dimensions | Endpoint |
|---|---|---|---|
| `bm25` | sparse | — | none (computed in-process) |
| `BAAI/bge-m3` | dense | 1024 | TEI-compatible `/embed` |
| `text-embedding-3-small` | dense | 1536 | OpenAI-compatible `/embeddings` |
| `text-embedding-3-large` | dense | 3072 | OpenAI-compatible `/embeddings` |

Default is `["bm25"]`. Any combination is allowed — listing a dense model alongside
`bm25` gives hybrid retrieval. Sparse vectors have no declared width; the collection
sets `modifier=IDF` so Qdrant applies corpus weighting at query time while the
encoder supplies only BM25's term-frequency half.

`indexTypes` is fixed at creation: changing it drops and recreates the collection and
marks every completed file `out_of_sync`, since vector layout can't be patched in place.

> **Note:** retrieval is currently wired only into the RAG evaluation harness
> (`main.py evaluate rag`); it is not yet consumed by the live chat/answer flow.

The top-level `knowledge/` directory is a separate, earlier standalone prototype of
this service (its own `main.py` / `app.py`); the live application uses `app/`.

### Model Fleet (`models/`)

Self-hosted vLLM model servers (chat, embeddings, OCR) and their nginx reverse proxy
config live in [models/](models/). See [models/README.md](models/README.md) for GPU
allocation, routes, and how to run them.

---

## Local Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 20+ and Yarn
- PostgreSQL 16 and Qdrant (easiest via `docker compose up db qdrant`)

### Setup

```bash
git clone <repo-url>
cd RAG-Playground

# Copy and fill in environment variables
cp .env.example .env

# Install Python deps
uv sync

# Start Postgres and Qdrant (or point DATABASE_URL / QDRANT_URL at your own)
docker compose up -d db qdrant

# Apply database migrations
uv run python main.py migrate upgrade head

# Create an admin console user (prompts for username + password)
uv run python main.py createadmin
```

### Run (single command)

```bash
uv run python main.py dev
```

This installs frontend deps, starts the admin build (console + `widget.js`) in watch
mode (`vite build --watch`), then runs the API with `uvicorn --reload`. `Ctrl+C` stops
everything.

- Admin console: `http://localhost:8000/`
- Widget preview: `http://localhost:8000/dev` (only when `ENV=DEV`).

---

## CLI (`main.py`)

Invoke as `uv run python main.py <command>`.

| Command | Description |
|---|---|
| `dev` | Run the API with `--reload` and watch-build the front-end (console + `widget.js`) |
| `migrate <alembic args>` | Forwards to Alembic, e.g. `migrate upgrade head`, `migrate revision --autogenerate -m "msg"`, `migrate downgrade -1`, `migrate current` |
| `extract <folder> <out_dir> [-r]` | OCR every PDF in a folder to `<name>.json` chunk files |
| `createadmin` | Create an admin console user (prompts for credentials) |
| `evaluate llm` | LLM serving-capacity report |
| `evaluate rag` | RAG retrieval-metrics report |

---

## Environment Variables

Backend settings are loaded from `.env` (see `app/config.py`). OCR/embedding
credentials are read directly from the environment.

### Core

| Variable | Default | Description |
|---|---|---|
| `ENV` | `DEV` | Set to anything other than `DEV` to disable the `/dev` preview page |
| `LOG_LEVEL` | `info` | Logging level (`debug`, `info`, `warning`, `error`) |
| `AGENT_NAME` | `Somsi` | Display name of the AI agent |

### Generation

| Variable | Default | Description |
|---|---|---|
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL for the chat model |
| `OPENAI_API_KEY` | — | API key for that endpoint |
| `GENERATION_MODEL` | `gpt-4o-mini` | Model used to generate replies |

### Database & vector store

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/chat_gateway` | Async SQLAlchemy connection URL |
| `DB_ECHO` | `false` | Log emitted SQL |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant REST endpoint holding the child-chunk collections |
| `QDRANT_API_KEY` | — | Qdrant API key (optional for self-hosted) |

### Sessions & admin auth

| Variable | Default | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS allowlist |
| `SESSION_COOKIE_NAME` | `chat_session` | Chat session cookie name |
| `SESSION_COOKIE_SECURE` | `true` | Send the session cookie only over HTTPS |
| `SESSION_COOKIE_SAMESITE` | `none` | SameSite policy for the session cookie |
| `SESSION_TIMEOUT_MINUTES` | `30` | Idle timeout before a session is expired |
| `ADMIN_SECRET_KEY` | `change-me-in-production` | Key used to sign the admin session cookie — **set this in production** |
| `ADMIN_COOKIE_NAME` | `admin_session` | Admin session cookie name |
| `ADMIN_SESSION_HOURS` | `1` | Admin session lifetime |
| `STORAGE_PATH` | `.knowledge/storage` | Local directory for uploaded file blobs |

### OCR & embeddings (knowledge base)

| Variable | Default | Description |
|---|---|---|
| `TYPHOON_BASE_URL` | — | Typhoon OCR API base URL (OpenAI-compatible `/chat/completions`) |
| `TYPHOON_OCR_API_KEY` | — | Typhoon OCR API key |
| `TYPHOON_OCR_MODEL` | `typhoon-ai/typhoon-ocr-7b` | OCR model name |
| `TEI_EMBEDDING_BASE_URL` | — | TEI-compatible `/embed` endpoint for `BAAI/bge-m3` |
| `TEI_EMBEDDING_API_KEY` | — | API key for the embedding endpoint (optional for self-hosted) |

`OPENAI_BASE_URL` / `OPENAI_API_KEY` (see [Generation](#generation)) double as the
endpoint for the `text-embedding-3-*` index types.

---

## Database

PostgreSQL. Migrations live in `migrations/versions/` and are managed with Alembic via
`main.py migrate`.

Key tables: `admins`, `sessions`, `messages`, `knowledge_bases`, `knowledge_nodes`
(file/folder tree), and `knowledge_chunks` (parent chunks). Child chunks and their
vectors live in Qdrant, not Postgres.

Scalar/composite indexes are hand-written in the `a93aa38c3cca_add_retrieval_indexes`
migration: chunk ordering, node status/type, message lookups, and a partial index for
the admin "needs attention" session ranking.

## Vector store

Qdrant, with **one collection per knowledge base**, named by the knowledge base's id.
Each child chunk is one point:

- **Vectors** — one named vector per entry in the KB's `indexTypes`, the name being the
  index type itself (`bm25`, `BAAI/bge-m3`, …). Dense vectors are cosine; `bm25` is a
  sparse vector with `modifier=IDF`.
- **Payload** — `chunk_id` (the parent in `knowledge_chunks`), `node_id`, `content`,
  `source`, `pages`. No `kb_id`: the collection *is* the knowledge base.
- **Payload indexes** — keyword indexes on `chunk_id` and `node_id`.

Collections are created and dropped by `KnowledgeBaseService` alongside the
`knowledge_bases` row. Qdrant isn't in the Postgres transaction, so writes `flush()`
first, then upsert, then `commit()` — a Qdrant failure rolls the row back.

---

## Updating the Greeting

The greeting is rendered by the widget as a pinned first bubble; it is never persisted
and never reaches the backend. Pass `welcomeMessage` to `createChat()` on the embedding
page (see [Embedding the Widget](#embedding-the-widget)):

```js
widgets.createChat({
  welcomeMessage: 'สวัสดีครับ มีอะไรให้ช่วยไหม?',
});
```

---

## Docker

### Build and run

```bash
docker compose up --build
```

This starts three services — the API (on `http://localhost:9997`), a `postgres:16`
database (on `5432`, data persisted in the `pgdata` volume), and `qdrant/qdrant`
(on `6333`/`6334`, data persisted in the `qdrantdata` volume). Run migrations against
the running stack with:

```bash
docker compose exec api uv run python main.py migrate upgrade head
```

### How the image is built

The Dockerfile in `build/Dockerfile` uses a multi-stage build:

1. **admin-builder** — Node 20, builds the admin console *and* `widget.js` into
   `admin/dist`; receives the `ENABLE_KNOWLEDGE_BASE` build arg
2. **runtime** — Python 3.12 slim, installs uv, syncs Python deps from `uv.lock`, copies
   app code and the built front-end

The build context is the **project root** (`context: .`), since the Dockerfile lives in
`build/` but needs the whole repo.

### Environment variables

Edit the `environment:` block in `docker-compose.yaml` directly:

```yaml
environment:
  - LOG_LEVEL=info
  - AGENT_NAME=น้องนารักษ์
  - OPENAI_BASE_URL=https://api.openai.com/v1
  - OPENAI_API_KEY=sk-…
  - GENERATION_MODEL=gpt-4o-mini
  - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/chat_gateway
  - QDRANT_URL=http://qdrant:6333
```

---

## Embedding the Widget

Add the following to any HTML page:

```html
<script type="module" src="https://your-host/widget.js"></script>
<script type="module">
  widgets.createChat({
    backendUrl: 'https://your-host',   // optional, defaults to the script's own directory (see below)
    position: 'bottom-right',          // 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left'
    offsetX: 20,                       // horizontal offset in px
    offsetY: 20,                       // vertical offset in px
    waveColor: '#6366f1',              // color of the wave ring animation
    innerSize: 56,                     // avatar circle diameter in px
    outerSize: 80,                     // bounding box diameter in px (must be > innerSize)
    iconUrl: 'https://your-host/avatar.png', // avatar image; omitted → the agent's initial
    panelWidth: 384,                   // chat panel width in px
    panelHeight: 600,                  // chat panel height in px
    panelBg: '#ffffff',               // chat panel background color (any CSS color value)
    agentName: 'น้องรักษ์',            // agent display name shown in the header and on replies
    welcomeMessage: 'สวัสดีค่ะ',       // greeting text shown as the first bubble
  });
</script>
```

All parameters are optional — `createChat()` with no arguments works and uses the defaults above.

### Configuration reference

| Parameter | Default | Description |
|---|---|---|
| `backendUrl` | the script's directory | Base URL for API calls — see [resolution](#how-backendurl-is-resolved) |
| `position` | `'bottom-right'` | Corner to anchor the widget |
| `offsetX` | `20` | Horizontal offset from the edge in px |
| `offsetY` | `20` | Vertical offset from the edge in px |
| `waveColor` | `'#6366f1'` | Color of the wave ring animation on the chat head |
| `innerSize` | `56` | Avatar circle diameter in px |
| `outerSize` | `80` | Outer bounding box diameter in px — must be larger than `innerSize` |
| `iconUrl` | — | URL of the avatar image; when omitted the agent's first initial is drawn instead |
| `panelWidth` | `384` | Chat panel width in px |
| `panelHeight` | `600` | Chat panel height in px |
| `panelBg` | `'#ffffff'` | Chat panel background color — accepts any CSS color value |
| `agentName` | `'Assistant'` | Agent display name shown in the header and on replies |
| `welcomeMessage` | `'This is the widget panel.'` | Greeting text shown as the first bubble |

### How `backendUrl` is resolved

If `backendUrl` is not provided, the widget defaults to the **directory `widget.js` was
loaded from** (`new URL(".", import.meta.url)`). Since it is served at
`<app-base>/widget.js`, this resolves to `<app-base>` — exactly where the API lives. A
script loaded from `https://chat.example.com/widget.js` resolves to
`https://chat.example.com`, and API calls go to `https://chat.example.com/api/...`.

This is deliberately the script's path, **not** just the origin, so it survives being
served behind a reverse proxy under a sub-path. If nginx serves the gateway at
`https://example.com/chat/`, the script loads from `https://example.com/chat/widget.js`,
`backendUrl` resolves to `https://example.com/chat`, and calls correctly go to
`https://example.com/chat/api/...`. Self-hosted deployments therefore require no
configuration.

---

## API Reference

Chat is session-based: open the control stream first (it sets the session cookie), then
send messages. All request/response bodies are camelCase JSON.

### `POST /api/control`

Opens a per-session Server-Sent Events stream and sets the session cookie
(`SESSION_COOKIE_NAME`). Pass `?new=true` to force a fresh session instead of
reconnecting the cookie's session. The stream carries realtime events for the session:

| `type` | Description |
|---|---|
| `message.created` | A message (from the user, agent, or an intercepting admin) was persisted |
| `feedback.updated` | A message's like/dislike vote changed |

### `POST /api/messages`

Sends a user message on the cookie's session, persists it, and streams the agent's
reply back as Server-Sent Events. Requires a valid session cookie (open a control
stream first), otherwise returns `401`.

**Request body**
```json
{
  "sender": "user",
  "content": "Hello",
  "imageBase64": null,
  "imageMimeType": null
}
```

**Response** — `text/event-stream`, one JSON frame per `data:` line:

| `type` | Payload | Description |
|---|---|---|
| `tool_call` | `name` | A tool the agent started calling |
| `token` | `delta` | The next slice of the reply text |
| `done` | `id` | End of the reply; `id` is the persisted message |

The finished reply is also broadcast over the control stream as `message.created`, so a
client that renders both should reconcile on the `done` frame's `id`. If an admin has
**intercepted** the session, nothing is generated: the stream is a single `done` frame
with no `id`, and the admin's replies arrive over the control stream instead.

### `GET /api/messages`

Returns the cookie session's messages as a list of `ChatResponse`, oldest first. Capped
at the **newest 20** — there is no pagination, and older messages are not returned.

### `POST /api/messages/{message_id}/feedback`

Sets, switches, or clears a like/dislike on a message. Body: `{ "value": "like" }`,
`{ "value": "dislike" }`, or `{ "value": null }` to unvote. Feedback is also broadcast
as a `feedback.updated` event on the control stream.

### Admin API (`/api/admin/*`)

All routes except login/logout/me require a valid admin session cookie.

| Endpoint | Description |
|---|---|
| `POST /api/admin/login` | Authenticate an admin, set the admin session cookie |
| `POST /api/admin/logout` | Clear the admin session |
| `GET /api/admin/me` | Current admin identity |
| `GET /api/admin/chats/current` | Paginated list of active sessions (attention-ordered) |
| `GET /api/admin/chats/history` | Paginated session history (`from`/`to` filters) |
| `GET /api/admin/chats/{session_id}/messages` | Transcript of a session |
| `POST /api/admin/chats/{session_id}/messages` | Send a message into a session as the admin |
| `POST /api/admin/chats/{session_id}/intercept` | Take over (`intercept`) or watch (`audit`) a session; SSE stream |
| `GET /api/admin/notifications` | SSE stream of admin realtime events (e.g. list changes) |
| `POST /api/admin/knowledge` · `GET` · `GET /{kb_id}` · `PATCH /{kb_id}` | Manage knowledge bases |
| `POST /api/admin/knowledge/{kb_id}/folders` | Create a folder node |
| `POST /api/admin/knowledge/{kb_id}/files` | Upload files (multipart); queues background OCR + indexing |
| `GET /api/admin/knowledge/{kb_id}/nodes` | List nodes (optional `?parent=`) |
| `GET /api/admin/knowledge/{kb_id}/files/{node_id}` · `/download` | File detail / download the original blob |
| `POST /api/admin/knowledge/{kb_id}/files/{node_id}/resync` | Re-OCR and re-index a file |
| `DELETE /api/admin/knowledge/{kb_id}/nodes/{node_id}` | Delete a node |

### `GET /health`

Returns `{"status": "ok"}`. Use for load balancer / uptime checks.

### `GET /metrics`

Prometheus metrics.
