"""`main.py evaluate llm` — LLM serving capacity report. Thin entrypoint."""


def add_arguments(p):
    p.add_argument("--target", required=True, help="vLLM base URL, e.g. http://localhost:8000")
    p.add_argument("--model", required=True, help="served model id, e.g. Qwen/Qwen3.5-9B")
    p.add_argument("--scenarios", required=True,
                   help="ISL:OSL pairs, comma-sep, e.g. 4096:128,1024:256,512:1024")
    p.add_argument("--rates", required=True,
                   help="offered req/s ramp, comma-sep, e.g. 0.5,1,2,4,8,16")
    p.add_argument("--max-seconds", type=float, default=120, help="duration per run")
    p.add_argument("--slo-ttft-ms", type=float, default=1000.0, help="p95 TTFT SLO (ms)")
    p.add_argument("--slo-itl-ms", type=float, default=50.0, help="p95 ITL SLO (ms)")
    p.add_argument("--backend", default="openai_http")
    p.add_argument("--api-key", default=None,
                   help="API key for the endpoint, if required.")
    p.add_argument("--out", default="report.md")


def run(args):
    from commands.eval_utils.llm.runner import evaluate

    evaluate(args)
