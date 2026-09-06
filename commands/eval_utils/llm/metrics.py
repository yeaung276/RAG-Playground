"""Pulls the reported latency/throughput fields off a GenerativeBenchmark."""


def _p95(dist_status):
    """p95 of the successful-request distribution, or None."""
    try:
        return dist_status.successful.percentiles.p95
    except Exception:
        return None


def _median(dist_status):
    try:
        return dist_status.successful.median
    except Exception:
        return None


def _mean(dist_status):
    try:
        return dist_status.successful.mean
    except Exception:
        return None


def extract(bench):
    """Pull the reported fields off a GenerativeBenchmark into a flat dict."""
    if bench is None:
        return None
    m = bench.metrics
    ss = bench.scheduler_state
    succ = getattr(ss, "successful_requests", 0) or 0
    err = getattr(ss, "errored_requests", 0) or 0
    canc = getattr(ss, "cancelled_requests", 0) or 0
    total = succ + err + canc
    comp_pct = (100.0 * succ / total) if total else None
    return {
        "completed_pct": comp_pct,
        "e2e_p50": _median(m.request_latency),          # seconds
        "e2e_p95": _p95(m.request_latency),
        "ttft_p50": _median(m.time_to_first_token_ms),  # ms
        "ttft_p95": _p95(m.time_to_first_token_ms),
        "itl_p95": _p95(m.inter_token_latency_ms),       # ms
        "out_tok_s": _mean(m.output_tokens_per_second),
        "concurrency": _mean(m.request_concurrency),
    }
