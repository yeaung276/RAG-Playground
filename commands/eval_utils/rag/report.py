"""Renders the RAG eval results: a markdown report plus one line chart per
(config, metric).

`results` is a list of `(name, kb_id, config, metrics)`, where `metrics` is the
flat list produced by `build_metrics` — one object per (metric key, k). We regroup
those by key so each metric gets its own table and its own figure. The config is
echoed under each heading so a report is self-describing.

Each figure plots the metric against k, one line per question type plus a bold
"overall" reference line. k values are placed at evenly-spaced tick positions
(labelled 1/3/5/10) so an uneven step like 5->10 doesn't stretch the tail.

`output` is a directory: the markdown lands at `<output>/report.md` and charts
in `<output>/assets/`, linked with relative paths so the folder is portable.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "x"


def _group_by_key(metrics: list) -> dict[str, list]:
    """{metric key -> its objects, sorted by k}, preserving first-seen order."""
    grouped: dict[str, list] = {}
    for metric in metrics:
        grouped.setdefault(metric.key, []).append(metric)
    for key in grouped:
        grouped[key].sort(key=lambda m: m.k)
    return grouped


def _types(group: list) -> list[str]:
    return sorted({t for metric in group for t in metric.by_type()})


def _chart(name: str, key: str, group: list, path: Path) -> None:
    ks = [metric.k for metric in group]
    xs = list(range(len(ks)))  # evenly spaced; k step is uneven

    fig, ax = plt.subplots(figsize=(6, 4))
    for qtype in _types(group):
        ys = [metric.by_type().get(qtype, 0.0) for metric in group]
        ax.plot(xs, ys, marker="o", linewidth=1.5, label=qtype)
    ax.plot(
        xs,
        [metric.overall() for metric in group],
        marker="o",
        linewidth=3,
        color="black",
        label="overall",
    )

    ax.set_title(f"{name} — {key}")
    ax.set_xlabel("k")
    ax.set_ylabel(key)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def render_report(results, output: str) -> str:
    assets = Path(output) / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    lines = ["# RAG Retrieval Evaluation", ""]
    for name, kb_id, config, metrics in results:
        lines.append(f"## {name}")
        lines.append(f"`kb_id={kb_id}`")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(config, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

        for key, group in _group_by_key(metrics).items():
            types = _types(group)
            lines.append(f"### {key}")
            lines.append("")

            header = ["k", "overall", *types]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("|" + "|".join(["---"] * len(header)) + "|")
            for metric in group:
                by_type = metric.by_type()
                row = [str(metric.k), f"{metric.overall():.3f}"]
                row += [f"{by_type.get(t, 0.0):.3f}" for t in types]
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")

            chart = assets / f"{_slug(name)}_{_slug(key)}.png"
            _chart(name, key, group, chart)
            lines.append(f"![{name} {key}]({assets.name}/{chart.name})")
            lines.append("")

    return "\n".join(lines)
