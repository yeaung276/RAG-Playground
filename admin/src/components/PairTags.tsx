import type { Category } from '../api/datasets';
import { CATEGORY_DOT, UNTAGGED } from './categories';

/** A pair's category pill and label chips, rendered into the caller's wrapping flex row. */
export default function PairTags({ category, labels }: { category: Category; labels: string[] }) {
  return (
    <>
      <span className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2 py-0.5 font-medium text-slate-600">
        <span className={`size-1.5 rounded-full ${CATEGORY_DOT[category]}`} />
        {category}
      </span>
      {labels.map((l) => (
        <span key={l} className="rounded-full bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700">
          {l}
        </span>
      ))}
      {labels.length === 0 && (
        <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-500">
          {UNTAGGED}
        </span>
      )}
    </>
  );
}
