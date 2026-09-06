import {
  createElement,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import type { Chunk } from '../api/types';

/** Longest suffix of `a` that is also a prefix of `b` (their overlap length). */
function overlapLen(a: string, b: string): number {
  for (let k = Math.min(a.length, b.length); k > 0; k--) {
    if (a.endsWith(b.slice(0, k))) return k;
  }
  return 0;
}

interface Range {
  id: string;
  seq: number;
  start: number;
  end: number;
}

/**
 * Recombine ordered chunks into one continuous string, dropping the overlap
 * where each chunk's prefix repeats the previous chunk's suffix. The shared
 * region stays with the earlier chunk, so the result partitions cleanly into
 * one contiguous range per chunk.
 */
function combine(chunks: Chunk[]): { text: string; ranges: Range[] } {
  let text = '';
  const ranges: Range[] = [];
  for (const c of chunks) {
    const start = text.length;
    text += c.content.slice(overlapLen(text, c.content));
    ranges.push({ id: c.id, seq: c.seq, start, end: text.length });
  }
  return { text, ranges };
}

// Block-level tags worth highlighting individually. Leaf-ish blocks (not ul/ol)
// so a chunk that spans several of them lights up as a group.
const BLOCK_TAGS = [
  'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'pre', 'table',
] as const;

type BlockProps = {
  node?: { position?: { start?: { offset?: number } } };
  children?: ReactNode;
} & Record<string, unknown>;

interface Props {
  chunks: Chunk[];
}

/**
 * Renders a file's chunks as one continuous markdown document. Hovering any
 * text highlights every block belonging to that chunk and shows its number.
 * Each markdown block is mapped to a chunk via its source offset, so
 * highlighting is per-block (a block straddling a boundary is attributed to
 * the chunk at its start).
 */
export default function ChunkedMarkdown({ chunks }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const { text, ranges } = useMemo(() => combine(chunks), [chunks]);
  const [seq, setSeq] = useState<number | null>(null);
  const activeId = useRef<string | null>(null);

  const seqById = useMemo(
    () => new Map(ranges.map((r) => [r.id, r.seq])),
    [ranges],
  );

  const components = useMemo<Components>(() => {
    const chunkAt = (offset: number): string | undefined => {
      for (const r of ranges) if (offset >= r.start && offset < r.end) return r.id;
      return ranges[ranges.length - 1]?.id;
    };
    const make = (tag: string) => {
      const Block = ({ node, children, ...props }: BlockProps) => {
        const offset = node?.position?.start?.offset;
        const id = offset !== undefined ? chunkAt(offset) : undefined;
        return createElement(tag, { ...props, 'data-chunk': id }, children);
      };
      return Block;
    };
    return Object.fromEntries(BLOCK_TAGS.map((t) => [t, make(t)])) as Components;
  }, [ranges]);

  // Memoized so hover state changes (the badge) never re-parse the markdown.
  const rendered = useMemo(
    () => (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={components}
      >
        {text}
      </ReactMarkdown>
    ),
    [text, components],
  );

  // Highlight via classList (no re-parse); only touch React state when the
  // hovered chunk actually changes, to drive the badge.
  function hover(id: string | null) {
    if (id === activeId.current) return;
    activeId.current = id;
    ref.current?.querySelectorAll<HTMLElement>('[data-chunk]').forEach((el) => {
      el.classList.toggle('chunk-hl', id !== null && el.dataset.chunk === id);
    });
    setSeq(id !== null ? seqById.get(id) ?? null : null);
  }

  return (
    <div
      ref={ref}
      className="markdown relative"
      onMouseOver={(e) => {
        // Only react to actual blocks. The margins/gaps between blocks aren't
        // inside any [data-chunk], so ignore them (don't clear) — otherwise
        // sweeping across a within-chunk gap flickers the highlight on and off.
        const id = (e.target as HTMLElement).closest<HTMLElement>('[data-chunk]')
          ?.dataset.chunk;
        if (id) hover(id);
      }}
      onMouseLeave={() => hover(null)}
    >
      {seq !== null && (
        <div className="pointer-events-none sticky top-0 z-10 h-0 text-right">
          <span className="inline-block rounded-full bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white shadow-md">
            Chunk {seq + 1}
          </span>
        </div>
      )}
      {rendered}
    </div>
  );
}
