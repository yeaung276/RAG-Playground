import {
  ArrowLeft,
  CheckCircle2,
  RefreshCw,
  Tag,
  TriangleAlert,
  XCircle,
} from 'lucide-react';

const input =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100';

/** Categories are structural — one per pair, fixed set. Labels are the user's own, many per pair. */
const CATEGORY_DOT = {
  simple: 'bg-indigo-500',
  reasoning: 'bg-cyan-400',
  multi_context: 'bg-amber-400',
  conditional: 'bg-violet-400',
};

/** A definition strip: reference detail, deliberately quieter than the metrics above it. */
function Spec({ items }: { items: [string, string][] }) {
  return (
    <dl className="grid gap-x-8 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
      {items.map(([term, value]) => (
        <div key={term} className="flex items-baseline justify-between gap-3 text-xs">
          <dt className="text-slate-400">{term}</dt>
          <dd className="truncate font-medium text-slate-600">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** A score against its baseline: the fill is this run, the tick is what it is being compared to. */
function Meter({
  label,
  score,
  baseline,
  tone = 'violet',
}: {
  label: string;
  score: number;
  baseline: number;
  tone?: 'violet' | 'cyan' | 'amber';
}) {
  const delta = score - baseline;
  const fill = {
    violet: 'bg-violet-500',
    cyan: 'bg-cyan-500',
    amber: 'bg-amber-500',
  }[tone];

  return (
    <div>
      <div className="mb-1.5 flex items-baseline gap-2 text-xs">
        <span className="font-medium text-slate-600">{label}</span>
        <span className="ml-auto tabular-nums text-slate-900">{score.toFixed(2)}</span>
        <span
          className={`w-11 text-right tabular-nums ${
            delta > 0 ? 'text-green-600' : delta < 0 ? 'text-red-600' : 'text-slate-400'
          }`}
        >
          {delta > 0 ? '+' : ''}
          {delta.toFixed(2)}
        </span>
      </div>
      <div className="relative h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${fill}`} style={{ width: `${score * 100}%` }} />
        <span
          className="absolute -top-0.5 h-3 w-0.5 rounded-full bg-slate-400"
          style={{ left: `${baseline * 100}%` }}
          title={`baseline ${baseline.toFixed(2)}`}
        />
      </div>
    </div>
  );
}

/** Hierarchy: the verdict, then where it moved, then the individual failures, then the config. */
export default function ExperimentDetail({ onBack }: { onBack: () => void }) {
  return (
    <>
      <div className="mb-5 flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex size-8 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-base font-semibold text-slate-900">
            #128 · hybrid + reranker
          </h2>
          <p className="text-xs text-slate-400">
            support-faq-v3 · 120 pairs · finished 2h ago in 6m 12s
          </p>
        </div>
        <button className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
          <RefreshCw size={16} /> Re-run
        </button>
      </div>

      {/* 1 — the verdict */}
      <section className="mb-4 rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center gap-6">
          <div>
            <p className="text-xs font-medium text-slate-400">Overall</p>
            <p className="mt-0.5 flex items-baseline gap-2">
              <span className="text-3xl font-semibold tabular-nums text-slate-900">0.87</span>
              <span className="text-sm font-medium tabular-nums text-green-600">+0.04</span>
            </p>
            <p className="mt-0.5 text-xs text-slate-400">against #126 · vector only</p>
          </div>

          <div className="min-w-[200px] flex-1">
            <div className="flex h-3 overflow-hidden rounded-full">
              <span className="w-[72%] bg-green-500" />
              <span className="w-[18%] bg-amber-400" />
              <span className="w-[10%] bg-red-500" />
            </div>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs">
              <span className="flex items-center gap-1.5 text-slate-500">
                <CheckCircle2 size={13} className="text-green-500" /> 86 passed
              </span>
              <span className="flex items-center gap-1.5 text-slate-500">
                <TriangleAlert size={13} className="text-amber-500" /> 22 borderline
              </span>
              <span className="flex items-center gap-1.5 text-slate-500">
                <XCircle size={13} className="text-red-500" /> 12 failed
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 2 — where it moved */}
      <section className="mb-4 rounded-2xl border border-slate-200 bg-white p-5">
        <div className="mb-4 flex items-baseline justify-between">
          <h3 className="text-sm font-semibold text-slate-900">Metrics</h3>
          <span className="text-xs text-slate-400">tick marks the baseline</span>
        </div>

        <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
          <Meter label="Faithfulness" score={0.91} baseline={0.87} />
          <Meter label="Answer relevancy" score={0.87} baseline={0.85} />
          <Meter label="Answer correctness" score={0.84} baseline={0.84} />
          <Meter label="Citation accuracy" score={0.79} baseline={0.81} />
          <Meter label="Context precision" score={0.82} baseline={0.61} tone="cyan" />
          <Meter label="Context recall" score={0.74} baseline={0.66} tone="cyan" />
          <Meter label="Hit rate @ 5" score={0.93} baseline={0.88} tone="amber" />
          <Meter label="MRR @ 5" score={0.68} baseline={0.49} tone="amber" />
        </div>
      </section>

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <h3 className="border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-900">
            By category
          </h3>
          <Breakdown
            rows={[
              ['simple', 48, 0.94, '46 / 48', 'good'],
              ['reasoning', 30, 0.88, '26 / 30', 'good'],
              ['multi_context', 30, 0.71, '19 / 30', 'bad'],
              ['conditional', 12, 0.8, '8 / 12', 'warn'],
            ]}
            dotted
          />
        </section>

        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <h3 className="flex items-center gap-2 border-b border-slate-100 px-5 py-3.5 text-sm font-semibold text-slate-900">
            <Tag size={15} className="text-slate-400" /> By label
          </h3>
          <Breakdown
            rows={[
              ['billing', 38, 0.76, '27 / 38', 'bad'],
              ['auth', 44, 0.93, '42 / 44', 'good'],
              ['data-residency', 26, 0.89, '23 / 26', 'good'],
              ['untagged', 12, 0.78, '7 / 12', 'warn'],
            ]}
          />
        </section>
      </div>

      {/* 3 — the individual failures */}
      <section className="mb-4 overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3.5">
          <h3 className="mr-auto text-sm font-semibold text-slate-900">Results</h3>
          <select className={`${input} w-auto py-1.5 text-xs`} defaultValue="failed and borderline">
            <option>failed and borderline</option>
            <option>all 120</option>
            <option>failed only</option>
          </select>
          <select className={`${input} w-auto py-1.5 text-xs`} defaultValue="any category">
            <option>any category</option>
            <option>simple</option>
            <option>reasoning</option>
            <option>multi_context</option>
            <option>conditional</option>
          </select>
        </div>

        <ul className="divide-y divide-slate-100">
          <Result
            verdict="fail"
            score={0.21}
            category="multi_context"
            labels={['billing']}
            question="If my plan lapses, can I still transfer a subscription to another workspace?"
            answer="Subscriptions move automatically when you invite the new workspace owner."
            metrics="faithfulness 0.18 · relevancy 0.44 · recall 0.00"
            why="Nothing relevant retrieved — the transfer policy sits in a file the index never returned."
          />
          <Result
            verdict="fail"
            score={0.34}
            category="simple"
            labels={['billing']}
            question="What is the refund window for annual plans?"
            answer="Annual plans can be refunded within 60 days of purchase."
            metrics="faithfulness 0.30 · relevancy 0.71 · recall 1.00"
            why="Right chunk retrieved, answer contradicts it — the source says 30 days."
          />
          <Result
            verdict="warn"
            score={0.52}
            category="multi_context"
            labels={['data-residency']}
            question="Which regions store data at rest in the EU?"
            answer="Frankfurt and Dublin. Other regions are listed in the compliance guide."
            metrics="faithfulness 0.88 · relevancy 0.55 · recall 0.40"
            why="Only one of the two needed chunks made the cut, so the answer is half an answer."
          />
          <Result
            verdict="warn"
            score={0.58}
            category="conditional"
            labels={['auth']}
            question="Can I use my own embedding model with a hosted index?"
            answer="Yes, if the index was created with a matching dimension."
            metrics="faithfulness 0.90 · relevancy 0.61 · MRR 0.25"
            why="Relevant chunk ranked fourth; the condition was recovered but weakly supported."
          />
        </ul>

        <div className="border-t border-slate-100 px-5 py-3 text-center text-xs text-slate-400">
          Showing 4 of 34 · 1 2 3 … 9
        </div>
      </section>

      {/* 4 — reference */}
      <section className="rounded-2xl border border-slate-200 bg-white p-5">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Configuration
        </h3>
        <Spec
          items={[
            ['Dataset', 'support-faq-v3'],
            ['Knowledge base', 'Product Docs'],
            ['Embedding', 'bge-large-en-v1.5'],
            ['Reranker', 'bge-reranker-v2-m3'],
            ['Search', 'hybrid · α 0.5'],
            ['Candidates', '40 → 5'],
            ['Generation', 'gpt-4o · temp 0.2'],
            ['Prompt', 'support-v7'],
            ['Judge', 'gpt-4o-mini'],
            ['Cost', '$0.62'],
            ['Latency', '1.8s median'],
            ['Baseline', '#126 · vector only'],
          ]}
        />
      </section>
    </>
  );
}

function Breakdown({
  rows,
  dotted,
}: {
  rows: [string, number, number, string, 'good' | 'warn' | 'bad'][];
  dotted?: boolean;
}) {
  const tone = {
    good: 'text-green-600',
    warn: 'text-amber-600',
    bad: 'text-red-600',
  };

  return (
    <ul className="divide-y divide-slate-100">
      {rows.map(([name, pairs, score, pass, state]) => (
        <li key={name} className="flex items-center gap-3 px-5 py-3 text-sm hover:bg-slate-50">
          {dotted && (
            <span
              className={`size-2 shrink-0 rounded-full ${
                CATEGORY_DOT[name as keyof typeof CATEGORY_DOT]
              }`}
            />
          )}
          <span className="min-w-0 flex-1 truncate font-medium text-slate-900">{name}</span>
          <span className="w-10 shrink-0 text-right text-xs tabular-nums text-slate-400">
            {pairs}
          </span>
          <span className="w-20 shrink-0">
            <span className="block h-1.5 rounded-full bg-slate-100">
              <span
                className="block h-1.5 rounded-full bg-slate-400"
                style={{ width: `${score * 100}%` }}
              />
            </span>
          </span>
          <span className="w-9 shrink-0 text-right tabular-nums text-slate-900">
            {score.toFixed(2)}
          </span>
          <span className={`w-14 shrink-0 text-right text-xs tabular-nums ${tone[state]}`}>
            {pass}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Result({
  verdict,
  score,
  category,
  labels,
  question,
  answer,
  metrics,
  why,
}: {
  verdict: 'fail' | 'warn';
  score: number;
  category: keyof typeof CATEGORY_DOT;
  labels: string[];
  question: string;
  answer: string;
  metrics: string;
  why: string;
}) {
  return (
    <li className="flex items-start gap-3 px-5 py-4 hover:bg-slate-50">
      <span
        className={`mt-0.5 shrink-0 rounded-md px-2 py-0.5 text-xs font-medium tabular-nums ${
          verdict === 'fail' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
        }`}
      >
        {score.toFixed(2)}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-900">{question}</p>
        <p className="mt-1 border-l-2 border-slate-200 pl-3 text-sm text-slate-500">{answer}</p>
        <p className={`mt-1.5 text-xs ${verdict === 'fail' ? 'text-red-600' : 'text-amber-600'}`}>
          {why}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px]">
          <span className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2 py-0.5 font-medium text-slate-600">
            <span className={`size-1.5 rounded-full ${CATEGORY_DOT[category]}`} />
            {category}
          </span>
          {labels.map((l) => (
            <span
              key={l}
              className="rounded-full bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700"
            >
              {l}
            </span>
          ))}
          <span className="tabular-nums text-slate-400">{metrics}</span>
        </div>
      </div>
    </li>
  );
}
