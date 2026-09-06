"""Markdown rendering: SLO verdicts and the per-scenario results table."""


def fmt(v, spec=""):
    if v is None:
        return "—"
    try:
        return format(v, spec) if spec else str(v)
    except (ValueError, TypeError):
        return str(v)


def slo_flag(m, ttft_slo, itl_slo):
    if m is None or m.get("completed_pct") is None:
        return "❌ collapse"
    if m["completed_pct"] < 90:
        return "❌ collapse"
    ttft, itl = m.get("ttft_p95"), m.get("itl_p95")
    if ttft is not None and ttft > ttft_slo:
        return "❌ TTFT"
    if itl is not None and itl > itl_slo:
        return "❌ ITL"
    return "✅"


def build_table(rows):
    hdr = ["Offered Rate (req/s)", "Completed", "p50 E2E (s)", "p95 E2E (s)",
           "p50 TTFT (ms)", "p95 TTFT (ms)", "p95 ITL (ms)", "Output tok/s",
           "Mean Conc", "SLO"]
    lines = ["| " + " | ".join(hdr) + " |",
             "|" + "|".join(["---"] * len(hdr)) + "|"]
    for r in rows:
        m = r["metrics"] or {}
        cp = m.get("completed_pct")
        cells = [
            fmt(r["rate"]),
            f"{cp:.0f}%" if cp is not None else "—",
            fmt(m.get("e2e_p50"), ".1f"),
            fmt(m.get("e2e_p95"), ".1f"),
            fmt(m.get("ttft_p50"), ".0f"),
            fmt(m.get("ttft_p95"), ".0f"),
            fmt(m.get("itl_p95"), ".0f"),
            fmt(m.get("out_tok_s"), ".0f"),
            fmt(m.get("concurrency"), ".0f"),
            r["slo"],
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
