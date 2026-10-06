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
    chunkingModelId: z.string().nullable(),
    maxChunkSize: z
      .number({ message: 'Enter a number' })
      .int('Must be a whole number')
      .positive('Must be greater than 0'),
    minChunkSize: z
      .number({ message: 'Enter a number' })
      .int('Must be a whole number')
      .positive('Must be greater than 0'),
    indexTypes: z
      .array(
        z.discriminatedUnion('type', [
          z.object({ type: z.literal('bm25') }),
          z.object({ type: z.literal('vector'), modelId: z.string().min(1, 'Pick an embedding model') }),
        ]),
      )
      .min(1, 'Add at least one index'),
    reranker: z
      .discriminatedUnion('type', [
        z.object({
          type: z.literal('cross-encoder'),
          modelId: z.string().min(1, 'Pick a cross-encoder model'),
        }),
        z.object({
          type: z.literal('late-interaction'),
          modelId: z.string().min(1, 'Pick a late-interaction embedding model'),
        }),
      ])
      .nullable(),
    queryExpansion: z
      .object({ modelId: z.string().min(1, 'Pick a chat model') })
      .nullable(),
  })
  .refine((c) => c.minChunkSize < c.maxChunkSize, {
    path: ['minChunkSize'],
    message: 'Child chunk size must be smaller than parent chunk size',
  })
  .refine((c) => c.chunkingMethod !== 'semantic' || !!c.chunkingModelId, {
    path: ['chunkingModelId'],
    message: 'Semantic chunking needs an embedding model',
  });

export type KnowledgeBaseConfig = z.infer<typeof knowledgeBaseConfigSchema>;
export type IndexType = (typeof INDEX_TYPES)[number];
export type ChunkingMethod = (typeof CHUNKING_METHODS)[number];

/** Server defaults, restated for pre-filling forms. */
export const DEFAULT_CONFIG: KnowledgeBaseConfig = {
  chunkingMethod: 'semantic',
  chunkingModelId: null,
  maxChunkSize: 1024,
  minChunkSize: 256,
  indexTypes: [{ type: 'bm25' }],
  reranker: null,
  queryExpansion: null,
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
