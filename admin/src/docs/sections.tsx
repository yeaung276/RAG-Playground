import Agents from './Agents';
import Evaluation from './Evaluation';
import Knowledge from './Knowledge';
import Models from './Models';
import Widget from './Widget';

/** Docs topics: one article each, shared by the page and the sidebar. */
export const SECTIONS = [
  { slug: 'widget', label: 'Widget', group: 'Guides', body: Widget },
  { slug: 'evaluation', label: 'Evaluation', group: 'Guides', body: Evaluation },
  { slug: 'models', label: 'Models', group: 'Configuration', body: Models },
  { slug: 'knowledge', label: 'Knowledge Base', group: 'Configuration', body: Knowledge },
  { slug: 'agents', label: 'Agents', group: 'Configuration', body: Agents },
] as const;
