import { Link } from 'react-router-dom';
import datasetImg from './assets/dataset.png';
import comparisonImg from './assets/experiment-comparison.png';
import errorAnalysisImg from './assets/experiment-error-analysis.png';
import resultImg from './assets/experiment-result.png';
import { C, Figure, H2, H3, Note, P, Table } from './prose';

const DATASET_FIELDS: [string, string][] = [
  ['Archive', 'A .zip of text files to write questions from. Hidden files, __MACOSX folders and binaries are skipped.'],
  ['Dataset name', 'Lowercase letters, digits and hyphens, up to 48 characters. Experiments on it are named after it.'],
  ['Model', 'The chat model that writes the pairs. Only decoder models appear.'],
  ['Questions per file', '1–10 pairs written from each file.'],
  ['Category mix', 'The share of pairs per category, in percent. Must add up to 100.'],
  ['Labels', 'Optional tags of your own. The model tags each pair with every label that applies, or none.'],
];

const CATEGORIES: [string, string][] = [
  ['simple', 'Answered by one chunk, asked plainly.'],
  ['reasoning', 'Needs an inference over the chunk, not a lookup.'],
  ['multi_context', 'Needs two or more chunks combined.'],
  ['conditional', 'The answer depends on a condition in the question.'],
];

const DATASET_STATUSES: [string, string][] = [
  ['Queued', 'Waiting to start — reading the archive.'],
  ['Running', 'Writing pairs, file by file. The row shows the pair count and how many files are parsed.'],
  ['Ready', 'Every file has been read. The dataset can be used by experiments.'],
  ['Failed', 'Generation stopped and the row shows the error. Retry starts it again from the beginning.'],
];

const METRICS: [string, string][] = [
  ['Context precision', 'Share of the retrieved chunks that are relevant.'],
  ['Context recall', 'Share of the golden sentences found anywhere in the retrieved chunks.'],
  ['Hit rate', '1 if any retrieved chunk is relevant, otherwise 0.'],
  ['MRR', 'Mean reciprocal rank — 1 divided by the rank of the first relevant chunk, 0 if there is none.'],
];

const RUN_STATUSES: [string, string][] = [
  ['Queued', 'Waiting to start.'],
  ['Importing', 'New base only — indexing the dataset’s files into it.'],
  ['Running', 'Searching for every question and scoring the results.'],
  ['Success', 'Scores are in and the per-pair results can be opened.'],
  ['Failed', 'The run stopped. The detail page shows the error.'],
];

export default function Evaluation() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        Evaluation measures how well a knowledge base retrieves. A <b>dataset</b> is a set of
        question/answer pairs written by a model from your documents; an <b>experiment</b> searches
        a knowledge base with every question and scores what comes back. Both live on the{' '}
        <Link to="/evaluation" className="font-medium text-indigo-600 hover:text-indigo-700">
          Evaluation
        </Link>{' '}
        page, under the Datasets and Experiments tabs.
      </P>
      <P>
        Experiments score retrieval only — the agent and its answer are not involved.
      </P>

      <H2 id="datasets">Datasets</H2>
      <P>
        <C>New dataset</C> uploads an archive and starts generation in the background.
      </P>
      <Table
        head={['Field', 'What it means']}
        rows={DATASET_FIELDS.map(([field, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{field}</span>,
          description,
        ])}
      />

      <H3>Categories</H3>
      <P>
        Every pair has exactly one category, describing how the question relates to the text. The
        set is fixed; labels are where your own tags go.
      </P>
      <Table
        head={['Category', 'The question…']}
        rows={CATEGORIES.map(([category, description]) => [
          <span className="whitespace-nowrap font-mono text-[13px] text-slate-800">{category}</span>,
          description,
        ])}
      />

      <H3>What a pair holds</H3>
      <P>
        A question, its answer, the category, any labels, the source file, and the <b>golden
        text</b> — the passage from that file the answer comes from. Experiments score against the
        golden text.
      </P>

      <H3>Status</H3>
      <Table
        head={['Status', 'What it means']}
        rows={DATASET_STATUSES.map(([status, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{status}</span>,
          description,
        ])}
      />
      <P>
        Open a dataset to see it. The <b>Data</b> tab shows its composition by category and label,
        the generator model, and every pair — filter by category or label, and expand a pair to
        read its golden text. The <b>Experiments</b> tab charts each metric across every
        successful run on the dataset, oldest first.
      </P>
      <Figure
        src={datasetImg}
        alt="Dataset page showing category and label composition, generator details, and the list of pairs"
        caption="A dataset's Data tab: composition, generator, and the pairs themselves."
      />
      <Figure
        src={comparisonImg}
        alt="Dataset Experiments tab with a line chart of scores over runs and the list of runs below"
        caption="The Experiments tab: every metric across runs, with each run's config summarised."
      />

      <H2 id="experiments">Experiments</H2>
      <P>
        <C>New experiment</C> picks a ready dataset, a knowledge base to search, how to search it,
        and which metrics to compute. Runs are named after the dataset and numbered —{' '}
        <C>support-faq #3</C>.
      </P>

      <H3>Knowledge base</H3>
      <P>
        Leave it on <b>New base</b> and the form asks for chunking, indexing, reranker and HyDE
        settings — the same fields as creating a base on the Knowledge page. The run creates that
        base, named <C>exp-</C> plus the run's name, and indexes the dataset's files into it
        before scoring.
      </P>
      <P>
        Picking an existing base skips importing and searches it as it is. Use one an earlier
        experiment on the same dataset built: a chunk only counts as relevant if it comes from the
        pair's source file, matched by file name.
      </P>

      <H3>Retrieval</H3>
      <P>
        Top K, Rerank on, Rerank pool and Prefetch limit work exactly as on an agent's Knowledge
        tab. HyDE has no switch here — it runs whenever the base has a HyDE model.
      </P>

      <H3>Metrics</H3>
      <P>
        The golden text is split into sentences. A retrieved chunk is <b>relevant</b> when it comes
        from the pair's source file and contains at least one of those sentences — whitespace is
        ignored and Thai digits match Arabic ones.
      </P>
      <Table
        head={['Metric', 'What it measures']}
        rows={METRICS.map(([metric, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{metric}</span>,
          description,
        ])}
      />
      <P>
        Each score is averaged over every pair in the dataset. Each pair is also marked{' '}
        <b>full</b> (every golden sentence was found), <b>partial</b> (some were) or <b>miss</b>{' '}
        (none were), whichever metrics you picked.
      </P>

      <H3>Status</H3>
      <Table
        head={['Status', 'What it means']}
        rows={RUN_STATUSES.map(([status, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{status}</span>,
          description,
        ])}
      />

      <H2 id="results">Reading results</H2>
      <P>
        An experiment's page shows the config it ran with, then its scores. Each score is a bar for
        this run, with a tick marking the best earlier run on the same dataset and the difference
        between them beside it. <b>By category</b> and <b>By label</b> break the run down by pair
        group — how many pairs each holds and their average score — so weak question types stand
        out.
      </P>
      <Figure
        src={resultImg}
        alt="Experiment page with the config snapshot, metric bars, breakdowns by category and label, and the results list"
        caption="An experiment: the config it ran with, its scores against the best so far, and the breakdowns."
      />
      <P>
        Under <b>Results</b>, filter pairs by status, category or label. Opening a pair shows the
        question, the expected answer, the golden text, and the retrieved chunks in rank order
        with their scores and the golden sentences they contain highlighted.
      </P>
      <Figure
        src={errorAnalysisImg}
        alt="Pair dialog showing the actual answer, the golden text, and retrieved chunks with golden sentences highlighted"
        caption="One pair up close — highlights show exactly which golden sentences each chunk caught."
      />
      <Note title="Rerun keeps the base">
        <C>Rerun</C> clears the scores and runs the search again against the same base, without
        importing files again. Use it after changing something outside the run, such as a model
        endpoint.
      </Note>
    </>
  );
}
