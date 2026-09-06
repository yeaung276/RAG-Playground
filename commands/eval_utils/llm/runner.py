"""Sweeps (scenario x rate), runs one guidellm point each, writes the report."""
import sys
from pathlib import Path

from commands.eval_utils.llm.benchmark import run_point
from commands.eval_utils.llm.metrics import extract
from commands.eval_utils.llm.report import build_table, fmt, slo_flag


def evaluate(args):
    scenarios = [tuple(int(x) for x in s.split(":")) for s in args.scenarios.split(",")]
    rates = [float(x) for x in args.rates.split(",")]

    md = [
        "# LLM Serving Capacity Report",
        "",
        f"**Model:** {args.model}  ",
        f"**Target:** {args.target}  ",
        f"**SLO:** p95 TTFT <= {args.slo_ttft_ms:.0f}ms, p95 ITL <= {args.slo_itl_ms:.0f}ms  ",
        f"**Per-run duration:** {args.max_seconds:.0f}s",
        "",
    ]

    for isl, osl in scenarios:
        print(f"[scenario] ISL={isl} OSL={osl}", file=sys.stderr)
        rows = []
        for rate in rates:
            print(f"  rate={rate}", file=sys.stderr)
            bench = run_point(
                target=args.target,
                model=args.model,
                backend=args.backend,
                api_key=args.api_key,
                isl=isl,
                osl=osl,
                rate=rate,
                max_seconds=args.max_seconds,
            )
            metrics = extract(bench)
            rows.append({
                "rate": rate,
                "metrics": metrics,
                "slo": slo_flag(metrics, args.slo_ttft_ms, args.slo_itl_ms),
            })
        knee = next((r["rate"] for r in reversed(rows) if r["slo"] == "✅"), None)
        md.append(f"## Scenario -- ISL {isl} / OSL {osl}")
        md.append("")
        md.append(build_table(rows))
        md.append("")
        md.append(f"**Knee (max sustainable rate): {fmt(knee)} req/s**"
                  if knee else "**Knee: none passed SLO**")
        md.append("")

    Path(args.out).write_text("\n".join(md))
    print(f"\nWrote {args.out}", file=sys.stderr)
