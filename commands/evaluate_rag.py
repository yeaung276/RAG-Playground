"""`main.py evaluate rag` — RAG retrieval evaluation.

Thin entrypoint: validate args, apply the env file, then hand off to the runner.
App imports are deferred until after the env file is loaded (settings + db engine
build at import time).
"""
import asyncio

DEFAULT_METRICS = "recall,precision,mrr,map,ndcg"
DEFAULT_TOPK = "1,3,5,10"


def add_arguments(p):
    p.add_argument("--dataset", required=True,
                   help="dataset dir with texts/*.json and eval/*.jsonl (or hf:<id>)")
    p.add_argument("--config", action="append", metavar="NAME=PATH", default=[],
                   help="IndexingConfig JSON, repeatable. 'name=path' or 'path'.")
    p.add_argument("--env", help="env file loaded before app settings are built")
    p.add_argument("--metrics", default=DEFAULT_METRICS,
                   help=f"comma-sep metrics (default: {DEFAULT_METRICS})")
    p.add_argument("--top-k", default=DEFAULT_TOPK,
                   help=f"comma-sep k values (default: {DEFAULT_TOPK})")
    p.add_argument("--kb-id", help="existing kb to query; required with --skip-index")
    p.add_argument("--skip-index", action="store_true",
                   help="query an existing --kb-id instead of indexing")
    p.add_argument("--cleanup-after-eval", action="store_true",
                   help="delete the on-demand kb (+ nodes/chunks/embeddings) when done")
    p.add_argument("--limit", type=int, help="evaluate only the first N questions")
    p.add_argument("--output", default="rag_report",
                   help="output dir for the report (report.md + assets/)")


def run(args):
    if args.skip_index and not args.kb_id:
        raise SystemExit("Error: --skip-index requires --kb-id")
    if args.skip_index and len(args.config) != 1:
        raise SystemExit("Error: --skip-index needs exactly one --config (query embedder)")
    if not args.config:
        raise SystemExit("Error: at least one --config is required")

    if args.env:
        from dotenv import load_dotenv
        load_dotenv(args.env, override=True)

    from commands.eval_utils.rag.runner import EvalOptions, RagEvaluator

    asyncio.run(RagEvaluator(EvalOptions.from_args(args)).run())
