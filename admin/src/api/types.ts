export type NodeType = 'file' | 'folder';

/**
 * OCR/extraction lifecycle. Absent (null) for folders and unsupported files.
 * `out_of_sync` = previously extracted, but the base config changed since, so
 * the content should be re-processed (resynced).
 */
export type NodeStatus = 'processing' | 'completed' | 'failed' | 'out_of_sync';

// Config type + its validation schema live in ./config (zod-derived).
export type { KnowledgeBaseConfig } from './config';
import type { KnowledgeBaseConfig } from './config';

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  config: KnowledgeBaseConfig;
  fileCount: number;
  createdAt: string;
}

export interface FileNode {
  id: string;
  kbId: string;
  parentId: string | null;
  name: string;
  type: NodeType;
  size: number | null;
  mimeType: string | null;
  status: NodeStatus | null;
  error: string | null;
  updatedAt: string;
}

/** One unit of extracted content for a file, ordered by `seq`. */
export interface Chunk {
  id: string;
  seq: number;
  content: string;
}

/**
 * A file plus its extracted chunks and the config snapshot used to process it.
 * Backs the detail drawer.
 */
export type FileDetail = FileNode & {
  config: KnowledgeBaseConfig | null;
  chunks: Chunk[];
};
