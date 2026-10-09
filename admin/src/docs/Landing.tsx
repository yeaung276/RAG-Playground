import { Link } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Bot,
  Check,
  Database,
  FlaskConical,
  Target,
  type LucideIcon,
} from 'lucide-react';
import agentsImg from './assets/agents.png';
import datasetImg from './assets/dataset.png';
import comparisonImg from './assets/experiment-comparison.png';
import errorAnalysisImg from './assets/experiment-error-analysis.png';
import resultImg from './assets/experiment-result.png';
import kbConfigImg from './assets/knowledge-base-config.png';
import kbFilesImg from './assets/knowledge-base.png';
import tracingImg from './assets/tracing-and-testing-agent.png';
import { Snippet } from './prose';
import { SECTIONS } from './sections';
import { SNIPPET } from './Widget';

const CAPABILITIES = [
  'Hybrid BM25 + dense search',
  'Cross-encoder & late-interaction reranking',
  'HyDE query expansion',
  'OCR for PDFs and scans',
  'Multi-agent handoffs',
  'Encrypted model keys',
];

const STEPS: [string, string][] = [
  ['Register models', 'Point at any OpenAI, TEI, Cohere or Gemini endpoint — chat, embeddings or rerankers.'],
  ['Index documents', 'Upload files into a knowledge base and pick how they are chunked, indexed and reranked.'],
  ['Configure agents', 'Give each agent a prompt, tools, knowledge and handoffs, then test the roster live.'],
  ['Measure and ship', 'Score retrieval on generated datasets, then embed the chat widget on your site.'],
];

const FEATURES: {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  body: string;
  points: string[];
  img: string;
  alt: string;
  doc: string;
}[] = [
  {
    icon: Bot,
    eyebrow: 'Agents',
    title: 'Configure agents, not code',
    body: 'Give each agent a model, a system prompt, HTTP tools and a knowledge base. Add more agents and let them hand conversations to each other — all from one screen, with nothing to deploy.',
    points: [
      'HTTP tools with {{placeholder}} parameters and encrypted credentials',
      'Automatic or hand-written handoff rules between agents',
      'Test the whole roster live, with a full trace of every tool call',
    ],
    img: agentsImg,
    alt: 'Agents page with the roster and the selected agent’s settings',
    doc: 'agents',
  },
  {
    icon: BookOpen,
    eyebrow: 'Knowledge',
    title: 'Search tuned to your documents',
    body: 'Upload PDFs, scans and text into a folder tree. Documents are read with OCR, split into small-to-big chunks, and indexed for keyword and semantic search at once.',
    points: [
      'Fix-sized, recursive or semantic chunking',
      'BM25 and dense indexes fused into one ranking',
      'Optional reranking and HyDE, per knowledge base',
    ],
    img: kbConfigImg,
    alt: 'New knowledge dialog with chunking, indexing and retrieval settings',
    doc: 'knowledge',
  },
  {
    icon: Database,
    eyebrow: 'Datasets',
    title: 'Ground truth, written for you',
    body: 'Hand over a zip of documents and a chat model writes question/answer pairs from them, each tied to the exact passage that answers it.',
    points: [
      'Simple, reasoning, multi-context and conditional questions',
      'Choose the mix and how many questions per file',
      'Tag pairs with your own labels to slice results later',
    ],
    img: datasetImg,
    alt: 'Dataset page with category and label composition and the generated pairs',
    doc: 'evaluation',
  },
  {
    icon: FlaskConical,
    eyebrow: 'Experiments',
    title: 'Measure every change',
    body: 'Run a dataset against any retrieval setup and get a score for every question — compared with your best run so far, and broken down by category and label.',
    points: [
      'Context precision, context recall, hit rate and MRR',
      'Index a fresh base per run, or reuse one',
      'Every run keeps a snapshot of the config it used',
    ],
    img: resultImg,
    alt: 'Experiment page with config snapshot, metric bars and breakdowns',
    doc: 'evaluation',
  },
  {
    icon: Target,
    eyebrow: 'Error analysis',
    title: 'See exactly why a question missed',
    body: 'Open any question to see the golden passage beside the chunks that came back, with the sentences each chunk caught highlighted. No guessing which setting to change next.',
    points: [
      'Every pair marked full, partial or miss',
      'Retrieved chunks in rank order, with their scores',
      'Filter by status, category or label',
    ],
    img: errorAnalysisImg,
    alt: 'Pair dialog with golden text and highlighted retrieved chunks',
    doc: 'evaluation',
  },
];

export default function Landing() {
  return (
    <div className="h-screen overflow-y-auto bg-white text-slate-900">
      <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-2">
            <BookOpen size={18} className="text-indigo-600" />
            <span className="font-semibold tracking-tight">Knowledge Service</span>
          </div>
          <nav className="flex items-center gap-1 text-sm">
            <Link
              to={`/docs/${SECTIONS[0].slug}`}
              className="rounded-lg px-3 py-1.5 font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            >
              Docs
            </Link>
            <Link
              to="/control"
              className="rounded-lg bg-indigo-600 px-3 py-1.5 font-medium text-white transition hover:bg-indigo-700"
            >
              Open console
            </Link>
          </nav>
        </div>
      </header>

      <section className="relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 -z-10 h-[520px] bg-gradient-to-b from-indigo-50 to-white" />
        <div className="mx-auto max-w-6xl px-6 pt-20 pb-12 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-white px-3 py-1 text-xs font-medium text-indigo-700">
            Retrieval-augmented agents, end to end
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
            Build agents that answer from your documents — and prove they do.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg leading-8 text-slate-600">
            Register models, index your documents, and wire up agents with tools and handoffs. Then
            measure retrieval with generated datasets and experiments — one console from first
            upload to a chat widget on your site.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              to="/control"
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700"
            >
              Open console <ArrowRight size={15} />
            </Link>
            <Link
              to={`/docs/${SECTIONS[0].slug}`}
              className="rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              Read the docs
            </Link>
          </div>
        </div>
        <div className="mx-auto max-w-5xl px-6">
          <Shot src={tracingImg} alt="Testing an agent with a live trace of its tool calls" />
        </div>
        <ul className="mx-auto mt-10 flex max-w-4xl flex-wrap justify-center gap-2 px-6">
          {CAPABILITIES.map((capability) => (
            <li
              key={capability}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600"
            >
              {capability}
            </li>
          ))}
        </ul>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="text-center text-sm font-semibold uppercase tracking-wide text-indigo-600">
          How it works
        </h2>
        <ol className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(([title, body], i) => (
            <li key={title} className="rounded-xl border border-slate-200 p-5">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">
                {i + 1}
              </span>
              <p className="mt-4 font-semibold">{title}</p>
              <p className="mt-1.5 text-sm leading-6 text-slate-600">{body}</p>
            </li>
          ))}
        </ol>
      </section>

      <div className="space-y-24 pb-24">
        {FEATURES.map(({ icon: Icon, eyebrow, title, body, points, img, alt, doc }, i) => (
          <section
            key={title}
            className="mx-auto grid max-w-6xl items-center gap-10 px-6 lg:grid-cols-5"
          >
            <div className={`lg:col-span-2 ${i % 2 ? 'lg:order-2' : ''}`}>
              <p className="flex items-center gap-2 text-sm font-semibold text-indigo-600">
                <Icon size={16} /> {eyebrow}
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight">{title}</h2>
              <p className="mt-4 leading-7 text-slate-600">{body}</p>
              <ul className="mt-5 space-y-2">
                {points.map((point) => (
                  <li key={point} className="flex gap-2 text-sm leading-6 text-slate-700">
                    <Check size={16} className="mt-1 shrink-0 text-indigo-600" />
                    {point}
                  </li>
                ))}
              </ul>
              <Link
                to={`/docs/${doc}`}
                className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-700"
              >
                Learn more <ArrowRight size={14} />
              </Link>
            </div>
            <div className="lg:col-span-3">
              <Shot src={img} alt={alt} />
            </div>
          </section>
        ))}
      </div>

      <section className="bg-slate-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-center text-3xl font-semibold tracking-tight">
            Everything in one console
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-center leading-7 text-slate-600">
            Your files, your runs and your trends sit side by side, so every change to chunking,
            indexing or reranking shows up as a number.
          </p>
          <div className="mt-10 grid gap-8 md:grid-cols-2">
            <figure>
              <Shot src={kbFilesImg} alt="A knowledge base's file browser" />
              <figcaption className="mt-3 text-center text-sm text-slate-500">
                Folders, uploads and per-file status.
              </figcaption>
            </figure>
            <figure>
              <Shot src={comparisonImg} alt="Scores over runs for one dataset" />
              <figcaption className="mt-3 text-center text-sm text-slate-500">
                Every metric tracked across runs.
              </figcaption>
            </figure>
          </div>
        </div>
      </section>

      <section className="bg-slate-900 py-20 text-white">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-6 lg:grid-cols-2">
          <div>
            <h2 className="text-3xl font-semibold tracking-tight">Ship it with two script tags</h2>
            <p className="mt-4 leading-7 text-slate-300">
              Drop the chat widget onto any page. It streams answers as they are written, lets
              visitors like or dislike a reply, and lets your team take over a live conversation
              from the Control Panel.
            </p>
            <Link
              to="/docs/widget"
              className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-indigo-300 hover:text-indigo-200"
            >
              Widget options <ArrowRight size={14} />
            </Link>
          </div>
          <Snippet code={SNIPPET} lang="html" />
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20 text-center">
        <h2 className="text-3xl font-semibold tracking-tight">Ready to try it?</h2>
        <p className="mt-3 text-slate-600">Open the console, or start with the docs.</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link
            to="/control"
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700"
          >
            Open console <ArrowRight size={15} />
          </Link>
          <Link
            to={`/docs/${SECTIONS[0].slug}`}
            className="rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            Read the docs
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-200">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-6 text-sm text-slate-500">
          <span>Knowledge Service</span>
          <nav className="flex flex-wrap gap-4">
            {SECTIONS.map((s) => (
              <Link key={s.slug} to={`/docs/${s.slug}`} className="hover:text-slate-800">
                {s.label}
              </Link>
            ))}
          </nav>
        </div>
      </footer>
    </div>
  );
}

function Shot({ src, alt }: { src: string; alt: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl shadow-slate-900/10">
      <div className="flex gap-1.5 border-b border-slate-200 bg-slate-50 px-3 py-2">
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
      </div>
      <img src={src} alt={alt} loading="lazy" className="block w-full" />
    </div>
  );
}
