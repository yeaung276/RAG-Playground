/**
 * Build-time feature flags, baked into the bundle by Vite from VITE_* env vars
 * (wired from docker-compose `build.args` → Dockerfile ARG). A feature is on
 * unless explicitly disabled, so local dev without the env var stays enabled.
 */
export const KNOWLEDGE_BASE_ENABLED =
  import.meta.env.VITE_ENABLE_KNOWLEDGE_BASE !== 'false';
