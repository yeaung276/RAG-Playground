import { ChevronLeft, ChevronRight } from 'lucide-react';

const step =
  'flex items-center gap-1 rounded-lg px-2.5 py-1.5 font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40';

/** Prev / Page x of y / Next. `page` is zero-based. */
export default function Pager({
  page,
  pageCount,
  onPage,
}: {
  page: number;
  pageCount: number;
  onPage: (page: number) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      <button onClick={() => onPage(Math.max(0, page - 1))} disabled={page === 0} className={step}>
        <ChevronLeft size={16} /> Prev
      </button>
      <span className="px-2 text-xs">
        Page {page + 1} of {pageCount}
      </span>
      <button
        onClick={() => onPage(Math.min(pageCount - 1, page + 1))}
        disabled={page >= pageCount - 1}
        className={step}
      >
        Next <ChevronRight size={16} />
      </button>
    </div>
  );
}
