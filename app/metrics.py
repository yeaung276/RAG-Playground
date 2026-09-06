from prometheus_client import Counter, Histogram
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
