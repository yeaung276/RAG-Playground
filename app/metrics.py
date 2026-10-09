from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# Default HTTP metrics (request count, latency, in-progress) plus a /metrics
# endpoint are provided by the instrumentator. /metrics and /health are
# excluded so scrapes and health checks don't pollute the request metrics.
instrumentator = Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/metrics", "/health"],
)

# Custom metrics for the generation (LLM) calls. These are the calls that
# dominate request latency, so we track them separately from the generic HTTP
# metrics above.
generation_requests_total = Counter(
    "generation_requests_total",
    "Total number of generation calls, labelled by outcome.",
    ["status"],
)

generation_duration_seconds = Histogram(
    "generation_duration_seconds",
    "Latency of generation calls in seconds.",
    buckets=(0.5, 1, 2.5, 5, 10, 20, 30, 45, 60, 90, 120),
)

# Background file processing: extract + index one uploaded file.
file_processing_total = Counter(
    "file_processing_total",
    "Files processed in the background, by outcome.",
    ["status"],
)
file_processing_duration_seconds = Histogram(
    "file_processing_duration_seconds",
    "Time to extract and index one file in seconds.",
    buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1200),
)
file_processing_in_progress = Gauge(
    "file_processing_in_progress",
    "Files currently being extracted and indexed.",
)

# OCR, one request per page.
ocr_pages_total = Counter(
    "ocr_pages_total",
    "Pages sent to OCR, by outcome.",
    ["status"],
)
ocr_page_duration_seconds = Histogram(
    "ocr_page_duration_seconds",
    "Latency of one OCR page request in seconds.",
    buckets=(1, 2.5, 5, 10, 20, 30, 60, 120, 300),
)
ocr_requests_in_flight = Gauge(
    "ocr_requests_in_flight",
    "OCR requests holding one of the concurrency slots.",
)

# Indexing.
indexed_chunks_total = Counter(
    "indexed_chunks_total",
    "Chunks written to the index, by level.",
    ["level"],
)
qdrant_upsert_duration_seconds = Histogram(
    "qdrant_upsert_duration_seconds",
    "Latency of one Qdrant upsert batch in seconds.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

# Retrieval.
retrieval_duration_seconds = Histogram(
    "retrieval_duration_seconds",
    "End-to-end latency of one knowledge search in seconds.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30),
)
retrieval_stage_duration_seconds = Histogram(
    "retrieval_stage_duration_seconds",
    "Latency of each knowledge search stage in seconds.",
    ["stage"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20),
)
retrieval_empty_total = Counter(
    "retrieval_empty_total",
    "Knowledge searches that returned nothing.",
)

# Registered model endpoints: embedding, reranking, late interaction.
model_request_duration_seconds = Histogram(
    "model_request_duration_seconds",
    "Latency of one request to a registered model in seconds.",
    ["model", "operation"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
model_request_errors_total = Counter(
    "model_request_errors_total",
    "Failed requests to a registered model.",
    ["model", "operation"],
)
model_batch_size = Histogram(
    "model_batch_size",
    "Texts sent in one request to a registered model.",
    ["model", "operation"],
    buckets=(1, 2, 4, 8, 16, 32, 64, 128),
)
model_rate_limit_wait_seconds = Histogram(
    "model_rate_limit_wait_seconds",
    "Time spent waiting on the per-process rate limiter in seconds.",
    ["model", "operation"],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
http_retries_total = Counter(
    "http_retries_total",
    "Outbound HTTP calls retried after a transient failure.",
    ["call"],
)

# Agents.
agent_model_call_duration_seconds = Histogram(
    "agent_model_call_duration_seconds",
    "Latency of one model call made by an agent in seconds.",
    ["agent"],
    buckets=(0.25, 0.5, 1, 2.5, 5, 10, 20, 30, 60, 120),
)
agent_tokens_total = Counter(
    "agent_tokens_total",
    "Tokens used by agents, by kind.",
    ["agent", "kind"],
)
agent_tool_calls_total = Counter(
    "agent_tool_calls_total",
    "Tool calls made by agents, by outcome.",
    ["agent", "tool", "status"],
)
agent_tool_duration_seconds = Histogram(
    "agent_tool_duration_seconds",
    "Latency of one agent tool call in seconds.",
    ["tool"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
agent_handoffs_total = Counter(
    "agent_handoffs_total",
    "Conversations handed from one agent to another.",
    ["from_agent", "to_agent"],
)
agent_step_limit_total = Counter(
    "agent_step_limit_total",
    "Agent runs ended by the step limit.",
    ["agent"],
)

# Dataset generation.
dataset_generation_total = Counter(
    "dataset_generation_total",
    "Dataset generation runs, by outcome.",
    ["status"],
)
dataset_generation_duration_seconds = Histogram(
    "dataset_generation_duration_seconds",
    "Time to generate one dataset in seconds.",
    buckets=(10, 30, 60, 120, 300, 600, 1200, 1800, 3600),
)
dataset_pairs_generated_total = Counter(
    "dataset_pairs_generated_total",
    "Question/answer pairs written by dataset generation.",
)

# Experiments.
experiment_runs_total = Counter(
    "experiment_runs_total",
    "Experiment runs, by outcome.",
    ["status"],
)
experiment_stage_duration_seconds = Histogram(
    "experiment_stage_duration_seconds",
    "Time an experiment spends importing files and scoring, in seconds.",
    ["stage"],
    buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1200, 3600),
)

# Live chat.
sse_connections = Gauge(
    "sse_connections",
    "Open event streams, by stream.",
    ["stream"],
)
chat_session_events_total = Counter(
    "chat_session_events_total",
    "Chat session lifecycle events.",
    ["event"],
)
chat_takeovers_total = Counter(
    "chat_takeovers_total",
    "Admin take-overs of chat sessions, by action.",
    ["action"],
)
realtime_events_dropped_total = Counter(
    "realtime_events_dropped_total",
    "Realtime events that never reached a subscriber, by reason.",
    ["reason"],
)
realtime_reconnects_total = Counter(
    "realtime_reconnects_total",
    "Reconnects of the realtime listener to Postgres.",
)

# Quality and auth.
message_feedback_total = Counter(
    "message_feedback_total",
    "Feedback votes on agent replies.",
    ["value"],
)
admin_logins_total = Counter(
    "admin_logins_total",
    "Admin login attempts, by outcome.",
    ["status"],
)
