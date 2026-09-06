"""Runs one in-process guidellm benchmark point. Requires guidellm>=0.6.1."""
import asyncio
import sys


def run_point(*, target, model, backend, api_key, isl, osl, rate, max_seconds):
    """Run one in-process guidellm benchmark, return the first GenerativeBenchmark
    (or None on failure)."""
    from guidellm.benchmark.entrypoints import benchmark_generative_text
    from guidellm.benchmark.schemas.generative.entrypoints import (
        BenchmarkGenerativeTextArgs,
    )

    backend_kwargs = {"target": target, "model": model}
    if api_key:
        backend_kwargs["api_key"] = api_key
    ba = BenchmarkGenerativeTextArgs.model_validate({
        "target": target,
        "model": model,
        "data": [f"prompt_tokens={isl},output_tokens={osl}"],
        "backend": backend,
        "backend_kwargs": backend_kwargs,
        "profile": "constant",
        "rate": [float(rate)],
        "max_seconds": max_seconds,
    })
    try:
        report, _ = asyncio.run(benchmark_generative_text(ba))
    except Exception as e:
        print(f"  rate={rate}: FAILED {type(e).__name__}: {e}", file=sys.stderr)
        return None
    if not report.benchmarks:
        return None
    return report.benchmarks[0]
