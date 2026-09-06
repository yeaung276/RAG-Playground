import { z } from 'zod';

/** Selectable embedding models. Keep in sync with the server's EmbeddingModel. */
export const EMBEDDING_MODELS = [
  'BAAI/bge-m3',
  'text-embedding-3-small',
  'text-embedding-3-large',
] as const;

/**
 * Single source of truth for a knowledge base's chunking / embedding config.
 * Used to validate both the new-base modal and the config page, and mirrors
 * the server-side pydantic KnowledgeBaseConfig.
 */
export const knowledgeBaseConfigSchema = z
  .object({
    parentChunkSize: z
      .number({ message: 'Enter a number' })
      .int('Must be a whole number')
      .positive('Must be greater than 0'),
    childChunkSize: z
      .number({ message: 'Enter a number' })
      .int('Must be a whole number')
      .positive('Must be greater than 0'),
    embeddingModel: z.enum(EMBEDDING_MODELS),
  })
  .refine((c) => c.childChunkSize < c.parentChunkSize, {
    path: ['childChunkSize'],
    message: 'Child chunk size must be smaller than parent chunk size',
  });

export type KnowledgeBaseConfig = z.infer<typeof knowledgeBaseConfigSchema>;
export type EmbeddingModel = (typeof EMBEDDING_MODELS)[number];

/** Server defaults, restated for pre-filling forms. */
export const DEFAULT_CONFIG: KnowledgeBaseConfig = {
  parentChunkSize: 1024,
  childChunkSize: 256,
  embeddingModel: 'BAAI/bge-m3',
};

/** Per-field error messages ({} when the config is valid). */
export function configFieldErrors(
  config: KnowledgeBaseConfig,
): Partial<Record<keyof KnowledgeBaseConfig, string>> {
  const result = knowledgeBaseConfigSchema.safeParse(config);
  if (result.success) return {};
  const flat = z.flattenError(result.error).fieldErrors;
  return {
    parentChunkSize: flat.parentChunkSize?.[0],
    childChunkSize: flat.childChunkSize?.[0],
    embeddingModel: flat.embeddingModel?.[0],
  };
}
