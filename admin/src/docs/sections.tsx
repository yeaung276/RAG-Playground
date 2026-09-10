import Models from './Models';
import Widget from './Widget';

/** Docs topics: one article each, shared by the page and the sidebar. */
export const SECTIONS = [
  { slug: 'widget', label: 'Widget', group: 'Guides', body: Widget },
  { slug: 'models', label: 'Models', group: 'Configuration', body: Models },
] as const;
