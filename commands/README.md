# Evaluation

Scripts for evaluating and comparing model serving endpoints and pipeline components.

## Setup

```
uv sync
```

Dev dependencies are managed with uv. To add a new one:

```
uv add --dev <package>
```

## Running scripts

Each script is standalone and run with uv:

```
uv run python <script>.py [args]
```

Pass `--help` to any script for its arguments.

---

## Scripts

### bench_report.py

Generates an LLM serving capacity report by sweeping a vLLM endpoint across ISL/OSL scenarios and offered request rates. Wraps `guidellm`: for each scenario it runs one fixed-rate benchmark per rate, parses guidellm's JSON output, applies latency SLOs, and writes one markdown table per scenario with the max sustainable rate (knee) called out.

Each scenario is an `ISL:OSL` pair (input sequence length : output sequence length), which controls whether the workload stresses prefill (high ISL, TTFT-bound) or decode (high OSL, ITL-bound). Output length is pinned (`output_tokens_stdev=0`) so latency comparisons across rates are clean. A run is marked `❌` when p95 TTFT or p95 ITL exceeds the SLO, or when fewer than 90% of requests complete (collapse); the knee is the highest rate still passing.

Requires `guidellm` on PATH (or invoked via `uv run guidellm`). Uses only guidellm's client-side metrics — no Prometheus or engine-side scraping.

Usage:

```
uv run evaluation/bench_report.py \
  --target http://localhost:8000 \
  --model Qwen/Qwen3.5-9B \
  --scenarios 4096:128,1024:256,512:1024 \
  --rates 0.5,1,2,4,8,16 \
  --out report.md
```

Arguments:

- `--target` — vLLM base URL (the `/v1/...` routes live under it). Required.
- `--model` — served model id, must match `/v1/models`. Required.
- `--scenarios` — comma-separated `ISL:OSL` pairs. Required.
- `--rates` — comma-separated offered request rates in req/s. Required.
- `--max-seconds` — duration per run (default 120).
- `--slo-ttft-ms` — p95 TTFT SLO in ms (default 1000).
- `--slo-itl-ms` — p95 ITL SLO in ms (default 50).
- `--backend` — guidellm backend (default `openai_http`).
- `--guidellm-cmd` — how to invoke guidellm, e.g. `"uv run guidellm"` (default `guidellm`).
- `--api-key` — API key for the endpoint, if required. Forwarded to guidellm. Falls back to `GUIDELLM__OPENAI__API_KEY` if unset.
- `--out` — output markdown path (default `report.md`).

Reported columns per scenario: offered rate, completed %, p50/p95 end-to-end latency (s), p50/p95 TTFT (ms), p95 ITL (ms), output tok/s, mean concurrency, and the SLO verdict.

Auth: if the endpoint requires a key (vLLM started with `--api-key`, or a gateway in front), pass it with `--api-key`:

```
uv run evaluation/bench_report.py --target ... --model ... --api-key your-key
```

If `--api-key` is omitted it falls back to the `GUIDELLM__OPENAI__API_KEY` env var. Keyless endpoints run with no key set, as-is.

Note: guidellm's JSON schema varies across versions. If report cells come out as `—`, check the field paths in `parse_guidellm_json` against your actual output JSON and adjust that one function.