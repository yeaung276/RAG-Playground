import type { Category } from '../api/datasets';

/** Categories are structural — one per pair, fixed set. Labels are the user's own, many per pair. */
export const CATEGORY_DOT: Record<Category, string> = {
  simple: 'bg-indigo-500',
  reasoning: 'bg-cyan-400',
  multi_context: 'bg-amber-400',
  conditional: 'bg-violet-400',
};

export const CATEGORIES = Object.keys(CATEGORY_DOT) as Category[];

export const UNTAGGED = 'untagged';
