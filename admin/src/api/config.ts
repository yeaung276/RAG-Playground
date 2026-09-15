import { z } from 'zod';

/** Selectable index types. Keep in sync with the server's IndexTypes. */
export const INDEX_TYPES = [
  'BAAI/bge-m3',
  'text-embedding-3-small',
  'text-embedding-3-large',
  'bm25',
] as const;

/** Keep in sync with the server's ChunkingStrategy. */
export const CHUNKING_METHODS = ['fix-sized', 'recursive', 'semantic'] as const;

/**
 * Single source of truth for a knowledge's chunking / indexing config.
 * Used to validate both the new-base modal and the config page, and mirrors
 * the server-side pydantic IndexingConfig.
 */
export const knowledgeBaseConfigSchema = z
  .object({
    chunkingMethod: z.enum(CHUNKING_METHODS),
    maxChunkSize: z
      .number({ message: 'Enter a number' })
      .int('Must be a whole number')
      .positive('Must be greater than 0'),
    minChunkSize: z
      .number({ message: 'Enter a number' })
      .int('Must be a whole number')
      .positive('Must be greater than 0'),
    indexTypes: z.array(z.enum(INDEX_TYPES)).min(1, 'Pick at least one index type'),
  })
  .refine((c) => c.minChunkSize < c.maxChunkSize, {
    path: ['minChunkSize'],
    message: 'Child chunk size must be smaller than parent chunk size',
  });

export type KnowledgeBaseConfig = z.infer<typeof knowledgeBaseConfigSchema>;
export type IndexType = (typeof INDEX_TYPES)[number];
export type ChunkingMethod = (typeof CHUNKING_METHODS)[number];

/** Server defaults, restated for pre-filling forms. */
export const DEFAULT_CONFIG: KnowledgeBaseConfig = {
  chunkingMethod: 'semantic',
  maxChunkSize: 1024,
  minChunkSize: 256,
  indexTypes: ['bm25'],
};

/** Per-field error messages ({} when the config is valid). */
export function configFieldErrors(
  config: KnowledgeBaseConfig,
): Partial<Record<keyof KnowledgeBaseConfig, string>> {
  const result = knowledgeBaseConfigSchema.safeParse(config);
  if (result.success) return {};
  const flat = z.flattenError(result.error).fieldErrors;
  return {
    chunkingMethod: flat.chunkingMethod?.[0],
    maxChunkSize: flat.maxChunkSize?.[0],
    minChunkSize: flat.minChunkSize?.[0],
    indexTypes: flat.indexTypes?.[0],
  };
}
