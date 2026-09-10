import { useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from './client';


export type SessionScope = 'current' | 'all';
export type SessionStatus = 'live' | 'away';
export type SessionPriority = 'urgent' | 'moderate' | 'low';

/** Backend sends a numeric priority score (0-100); bucket it for display.
 * Cutoffs mirror the backend's intent (low 0-33, moderate 34-66, urgent 67+). */
function toPriority(score: number): SessionPriority {
  if (score >= 67) return 'urgent';
  if (score >= 34) return 'moderate';
  return 'low';
}

export interface Session {
  id: string;
  status: SessionStatus;
  priority: SessionPriority;
  triggerMessage: string;
  upvotes: number;
  downvotes: number;
  createdAt: string;
}

export interface SessionPage {
  items: Session[];
  total: number;
  page: number;
  pageSize: number;
}

export interface DateRange {
  from?: string;
  to?: string;
}

export const keys = {
  sessions: (
    scope: SessionScope,
    page: number,
    pageSize: number,
    range: DateRange,
  ) => ['sessions', { scope, page, pageSize, ...range }] as const,
};

// Raw item shape from the admin chat list. status comes back raw and
// priority is a numeric score; map them to the table shape.
interface ApiChat {
  id: string;
  status: string;
  createdAt: string;
  triggerMessage: string | null;
  priority: number;
  upvotes: number;
  downvotes: number;
}

function toSession(c: ApiChat): Session {
  return {
    id: c.id,
    status: c.status === 'active' ? 'live' : 'away',
    priority: toPriority(c.priority),
    triggerMessage: c.triggerMessage ?? '',
    upvotes: c.upvotes,
    downvotes: c.downvotes,
    createdAt: c.createdAt,
  };
}

async function fetchSessions(
  scope: SessionScope,
  page: number,
  pageSize: number,
  range: DateRange,
): Promise<SessionPage> {
  const resource = scope === 'current' ? 'current' : 'history';
  const params = new URLSearchParams({
    page: String(page + 1),
    pageSize: String(pageSize),
  });
  if (range.from) params.set('from', range.from);
  if (range.to) params.set('to', range.to);
  const res = await fetch(`/api/admin/chats/${resource}?${params}`);
  if (res.status === 401 && !window.location.hash.startsWith('#/login')) {
    window.location.hash = '#/login';
  }
  if (!res.ok) throw new ApiError('Failed to load sessions', res.status);

  const data: { items: ApiChat[]; total: number; page: number; pageSize: number } =
    await res.json();
  return {
    items: data.items.map(toSession),
    total: data.total,
    page: data.page,
    pageSize: data.pageSize,
  };
}

export function useSessions(
  scope: SessionScope,
  page: number,
  pageSize: number,
  range: DateRange = {},
) {
  return useQuery({
    queryKey: keys.sessions(scope, page, pageSize, range),
    queryFn: () => fetchSessions(scope, page, pageSize, range),
  });
}

const DIRTY_DEBOUNCE_MS = 1000;
const DIRTY_MAX_WAIT_MS = 3000;

/** Opens the admin notification stream (GET /api/admin/notifications) on mount.
 * On `admin.list.dirty` it invalidates the session lists so they refetch. The
 * refetch is debounced (trailing DEBOUNCE, capped at MAX_WAIT) so a burst of
 * events coalesces into periodic refreshes instead of a request storm. */
export function useAdminNotifications() {
  const qc = useQueryClient();
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | null = null;
    let firstAt = 0;

    const flush = () => {
      timer = null;
      firstAt = 0;
      qc.invalidateQueries({ queryKey: ['sessions'] });
    };
    const scheduleRefetch = () => {
      const now = Date.now();
      if (!firstAt) firstAt = now;
      if (timer) clearTimeout(timer);
      const wait = Math.min(DIRTY_DEBOUNCE_MS, Math.max(0, firstAt + DIRTY_MAX_WAIT_MS - now));
      timer = setTimeout(flush, wait);
    };

    (async () => {
      try {
        const res = await fetch('/api/admin/notifications', {
          credentials: 'include',
          signal: controller.signal,
        });
        if (!res.ok || !res.body) return;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buffer.indexOf('\n\n')) !== -1) {
            const frame = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            const data = frame
              .split('\n')
              .filter((l) => l.startsWith('data:'))
              .map((l) => l.slice(5).trim())
              .join('\n');
            if (!data) continue;
            try {
              if (JSON.parse(data).type === 'admin.list.dirty') scheduleRefetch();
            } catch {
              // ignore malformed frame
            }
          }
        }
      } catch {
        // aborted (unmount) or network drop
      }
    })();

    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [qc]);
}

/** A single message in a session transcript, shaped for the chat view. */
export interface Message {
  id: string;
  sender: 'user' | 'agent' | 'system';
  content: string;
  feedback: 'like' | 'dislike' | null;
}

// Raw item from GET /api/admin/chats/{id}/messages (ChatResponse). `sender` is
// a free string ('user', 'system', or the agent name); collapse it to the UI type.
interface ApiMessage {
  id: string;
  sender: string;
  content: string | null;
  feedback: 'like' | 'dislike' | null;
}

function toSender(sender: string): Message['sender'] {
  if (sender === 'user') return 'user';
  if (sender === 'system') return 'system';
  return 'agent';
}

async function fetchMessages(sessionId: string): Promise<Message[]> {
  const res = await fetch(`/api/admin/chats/${sessionId}/messages`);
  if (res.status === 401 && !window.location.hash.startsWith('#/login')) {
    window.location.hash = '#/login';
  }
  if (!res.ok) throw new ApiError('Failed to load messages', res.status);
  const rows: ApiMessage[] = await res.json();
  return rows.map((r) => ({
    id: r.id,
    sender: toSender(r.sender),
    content: r.content ?? '',
    feedback: r.feedback ?? null,
  }));
}

export function useMessages(sessionId: string) {
  return useQuery({
    queryKey: ['messages', sessionId] as const,
    queryFn: () => fetchMessages(sessionId),
  });
}

/**
 * Opens the intercept/audit stream for the session. Its lifetime is the
 * intercept's lifetime: `mode=intercept` takes over on connect, and the backend
 * releases it when this connection closes (unmount / tab close aborts the
 * fetch). Every message in the session arrives as a `data:` frame and is handed
 * to onMessage, so the transcript stays live.
 */
export function useInterceptStream(
  sessionId: string,
  mode: 'intercept' | 'audit',
  handlers: {
    onMessage: (message: Message) => void;
    onFeedback: (id: string, feedback: Message['feedback']) => void;
  },
) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!sessionId) return;
    const controller = new AbortController();
    (async () => {
      try {
        const res = await fetch(
          `/api/admin/chats/${sessionId}/intercept?mode=${mode}`,
          { method: 'POST', credentials: 'include', signal: controller.signal },
        );
        if (!res.ok || !res.body) return;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buffer.indexOf('\n\n')) !== -1) {
            const frame = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            const data = frame
              .split('\n')
              .filter((l) => l.startsWith('data:'))
              .map((l) => l.slice(5).trim())
              .join('\n');
            if (!data) continue;
            try {
              const evt = JSON.parse(data);
              if (evt.type === 'message.created') {
                const m: ApiMessage = evt.data;
                handlersRef.current.onMessage({ id: m.id, sender: toSender(m.sender), content: m.content ?? '', feedback: m.feedback ?? null });
              } else if (evt.type === 'feedback.updated') {
                handlersRef.current.onFeedback(evt.data.id, evt.data.feedback ?? null);
              }
              // unknown event type: ignore
            } catch {
              // ignore malformed frame
            }
          }
        }
      } catch {
        // aborted (unmount) or network drop
      }
    })();
    return () => controller.abort();
  }, [sessionId, mode]);
}

/** Sends an admin message into the session; it is persisted and published, so
 * it reaches the widget and echoes back over this admin's intercept stream. */
export async function sendAdminMessage(sessionId: string, content: string): Promise<void> {
  const res = await fetch(`/api/admin/chats/${sessionId}/messages`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new ApiError('Failed to send message', res.status);
}
