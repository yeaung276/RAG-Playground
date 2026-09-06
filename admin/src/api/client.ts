// Same origin as the served app.
export const BASE = '/api/admin/knowledge';

/** Error carrying the server's `detail` message and HTTP status. */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function raise(res: Response): Promise<never> {
  let detail = 'Something went wrong';
  try {
    const data = await res.json();
    if (data && typeof data === 'object' && 'detail' in data) {
      detail = String((data as { detail: unknown }).detail);
    }
  } catch {
    /* non-JSON body — keep the default message */
  }
  throw new ApiError(detail, res.status);
}

interface RequestOptions {
  method?: string;
  /** JSON body — serialized and sent with a JSON content-type. */
  json?: unknown;
  /** Raw body (e.g. FormData) — sent as-is with no content-type header. */
  body?: BodyInit;
}

/** Thin fetch wrapper that returns parsed JSON and throws {@link ApiError}. */
export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const init: RequestInit = { method: opts.method ?? 'GET' };
  if (opts.json !== undefined) {
    init.headers = { 'Content-Type': 'application/json' };
    init.body = JSON.stringify(opts.json);
  } else if (opts.body !== undefined) {
    init.body = opts.body;
  }

  const res = await fetch(`${BASE}${path}`, init);
  if (res.status === 401) {
    if (!window.location.hash.startsWith('#/login')) window.location.hash = '#/login';
  }
  if (!res.ok) await raise(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Downloads are a binary blob, kept as a plain fetch. */
export async function downloadFile(kbId: string, nodeId: string): Promise<Blob> {
  const res = await fetch(`${BASE}/${kbId}/files/${nodeId}/download`);
  if (!res.ok) throw new Error('Download failed');
  return res.blob();
}

/** Pull a human-readable message out of a thrown error. */
export function errorMessage(err: unknown): string {
  if (err instanceof Error && err.message) return err.message;
  return 'Something went wrong';
}
