import { Link } from 'react-router-dom';
import kbConfigImg from './assets/knowledge-base-config.png';
import kbFilesImg from './assets/knowledge-base.png';
import { C, Figure, H2, H3, Note, P, Table } from './prose';

const CHUNKING: [string, string][] = [
  ['Method', 'How documents are split into parent chunks — fix-sized, recursive or semantic.'],
  ['Embedding model', 'Semantic only. A bi-encoder used to find topic breaks between sentences.'],
  ['Parent chunk size', 'Upper bound on a parent chunk, in characters. Parents are what an agent reads.'],
  ['Child chunk size', 'Must be smaller than the parent size. Used as the minimum chunk size by semantic chunking.'],
];

const METHODS: [string, string][] = [
  ['fix-sized', 'Cuts the text at the parent size, wherever that lands.'],
  ['recursive', 'Prefers natural breaks — paragraphs, then lines, then words — and only cuts mid-sentence when it has to.'],
  ['semantic', 'Embeds each sentence and splits where the topic shifts, then re-splits any parent over the size cap.'],
];

const RETRIEVAL: [string, string][] = [
  ['Reranker', 'None, Cross-encoder or Late interaction, plus the model to use. Agents and experiments can only rerank when the base has one.'],
  ['HyDE', 'Off, or a chat model that writes a hypothetical answer to search with in place of the query.'],
];

const STATUSES: [string, string][] = [
  ['Extracting…', 'Queued or in progress — the file is being read, chunked and indexed in the background.'],
  ['Extracted', 'Indexed and searchable.'],
  ['Failed', 'Extraction or indexing stopped. Hover for the error, then resync to try again.'],
  ['Out of sync', 'The base’s config changed after this file was indexed. Resync to re-process it.'],
];

export default function Knowledge() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        A knowledge base is a folder tree of documents, split into chunks and indexed so they can
        be searched. Agents search it through their <C>search_knowledge</C> tool, and experiments
        on the Evaluation page measure how well it retrieves. Bases are managed on the{' '}
        <Link to="/knowledge" className="font-medium text-indigo-600 hover:text-indigo-700">
          Knowledge
        </Link>{' '}
        page; the copy button on each row puts the base's id on your clipboard.
      </P>
      <P>
        Every model a base uses — embeddings, reranker, HyDE — must be registered on the Models page
        first.
      </P>
      <Figure
        src={kbConfigImg}
        alt="New knowledge dialog with Chunking, Indexing and Retrieval sections"
        caption="Creating a base: chunking, indexing and retrieval are set in one form."
      />

      <H2 id="chunking">Chunking</H2>
      <P>
        Chunking is two-level, "small-to-big". Each document is split into <b>parent</b> chunks,
        and every parent is split again into small <b>child</b> chunks of 512 characters with a
        40-character overlap. Children are what gets embedded and searched; a match returns its
        parent, so the agent reads a whole passage rather than a fragment.
      </P>
      <Table
        head={['Field', 'What it means']}
        rows={CHUNKING.map(([field, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{field}</span>,
          description,
        ])}
      />
      <H3>Methods</H3>
      <Table
        head={['Method', 'How it splits']}
        rows={METHODS.map(([method, description]) => [
          <span className="whitespace-nowrap font-mono text-[13px] text-slate-800">{method}</span>,
          description,
        ])}
      />

      <H2 id="indexing">Indexing</H2>
      <P>
        A base needs at least one index, and each index is one way of matching a query against the
        child chunks:
      </P>
      <P>
        <b>Sparse — BM25</b> matches keywords. It needs no model and can be added once.{' '}
        <b>Dense</b> matches meaning, using one registered bi-encoder per index; each model can be
        added once.
      </P>
      <P>
        Add more than one index for hybrid search — each index finds its own candidates and their
        rankings are fused into one list (reciprocal rank fusion, which rewards chunks that rank
        well in several indexes).
      </P>
      <Note title="Indexes are fixed by the base">
        The set of indexes decides the vector layout stored for every chunk, so agents and
        experiments can only search the indexes the base was built with.
      </Note>

      <H2 id="retrieval">Retrieval</H2>
      <P>
        These settings make extra stages available. Whether a search uses them is chosen by the
        caller — an agent's Knowledge tab, or an experiment's retrieval config.
      </P>
      <Table
        head={['Field', 'What it means']}
        rows={RETRIEVAL.map(([field, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{field}</span>,
          description,
        ])}
      />
      <H3>Rerankers</H3>
      <P>
        A <b>cross-encoder</b> reads the query and each candidate together and scores the pair. A{' '}
        <b>late interaction</b> model keeps one vector per token and scores by how well the query's
        tokens match the chunk's tokens. With late interaction the base also stores those
        per-token vectors for every parent chunk at indexing time, so uploads take longer and the
        base is larger.
      </P>
      <H3>HyDE</H3>
      <P>
        HyDE (hypothetical document embeddings) asks a chat model to write a short passage that
        would answer the question, then searches with that passage. It helps when questions are
        phrased very differently from the documents. Reranking still scores against the original
        query.
      </P>

      <H2 id="search-order">How a search runs</H2>
      <P>
        The query — or the HyDE passage — is embedded once per index. Each index contributes up to{' '}
        <C>Prefetch limit</C> child matches, the lists are fused, and matches are collapsed to
        distinct parents, keeping <C>Rerank pool</C> of them. If reranking is on, those are
        rescored, and the best <C>Top K</C> parents are returned.
      </P>

      <H2 id="files">Files</H2>
      <P>
        Open a base to browse its files. Drop files anywhere on the page to upload into the current
        folder, or create folders to organise them. Text files are read as-is; PDFs and images
        (PNG, JPEG, WebP, TIFF, BMP, GIF) are run through OCR one page at a time. Any other type is
        marked failed.
      </P>
      <Figure
        src={kbFilesImg}
        alt="File browser for a knowledge base, with the folder tree on the left and the file list on the right"
        caption="A base's files. The icon beside each name shows its status."
      />
      <Table
        head={['Status', 'What it means']}
        rows={STATUSES.map(([status, description]) => [
          <span className="whitespace-nowrap font-medium text-slate-800">{status}</span>,
          description,
        ])}
      />
      <P>
        Each row can be downloaded as the original file, resynced, or deleted. Double-click a file
        to see its type, size, the config it was indexed with, and the extracted content split
        into its parent chunks.
      </P>
      <Note title="Resync redoes everything">
        Resync re-extracts the file, including OCR, and re-indexes it with the base's current
        config. Deleting a file also removes its chunks from search; a folder can only be deleted
        once it is empty.
      </Note>
    </>
  );
}
