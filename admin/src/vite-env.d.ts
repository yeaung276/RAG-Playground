/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "false" hides the Knowledge Base feature in the admin console. */
  readonly VITE_ENABLE_KNOWLEDGE_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
