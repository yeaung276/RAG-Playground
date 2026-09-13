import { useCallback, useRef, useState } from 'react';
import { readFrames } from '../../api/sse';
import { useWidgetConfig } from '../config';
import { useControlEvent } from './useSession';

export type Feedback = 'like' | 'dislike';

/** A persisted message, as GET /api/messages and `message.created` deliver it. */
interface Wire {
  id: string;
  sender: string;
  content: string | null;
  feedback?: Feedback | null;
}

export interface ChatMessage {
  id: string;
  sender: string;
  content: string;
  feedback: Feedback | null;
  failed?: { content: string };
}

/** The reply arriving on the open POST /api/messages response. */
export interface Reply {
  content: string;
  tools: string[];
}

interface ReplyFrame {
  type: string;
  delta?: string;
  name?: string;
  id?: string;
}

const toMessage = (wire: Wire): ChatMessage => ({
  id: wire.id,
  sender: wire.sender,
  content: wire.content ?? '',
  feedback: wire.feedback ?? null,
});

export function useChat() {
  const { backendUrl, agentName } = useWidgetConfig();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [reply, setReply] = useState<Reply | null>(null);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const ingest = useCallback((wire: Wire) => {
    setMessages((prev) => {
      const message = toMessage(wire);
      const i = prev.findIndex((m) => m.id === message.id);
      if (i === -1) return [...prev, message];
      const next = prev.slice();
      next[i] = message;
      return next;
    });
  }, []);

  useControlEvent<Wire>('message.created', ingest);

  useControlEvent<void>('session.open', async () => {
    setMessages([]);
    setReply(null);
    setError(false);
    setLoading(true);
    try {
      const response = await fetch(`${backendUrl}/api/messages`, {
        credentials: 'include',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const rows: Wire[] = await response.json();
      setMessages(rows.map(toMessage));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  });

  const post = useCallback(
    async (content: string) => {
      const response = await fetch(`${backendUrl}/api/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ sender: 'user', content }),
      });
      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`);

      let text = '';
      const done: { id?: string } = {};
      setReply({ content: '', tools: [] });
      try {
        await readFrames<ReplyFrame>(response.body, (frame) => {
          if (frame.type === 'token') {
            text += frame.delta ?? '';
            setReply((current) => current && { ...current, content: text });
          } else if (frame.type === 'tool_call') {
            setReply(
              (current) =>
                current && { ...current, tools: [...current.tools, frame.name ?? ''] },
            );
          } else if (frame.type === 'done') {
            done.id = frame.id ?? undefined;
          }
        });
        // An intercepted session answers with a bare `done`: nothing was
        // generated and a human replies later over the control stream. Otherwise
        // adopt the id the reply was persisted under, so the control stream's
        // copy of it replaces this one instead of duplicating it.
        if (done.id) {
          ingest({ id: done.id, sender: agentName, content: text });
        }
      } finally {
        setReply(null);
      }
    },
    [backendUrl, agentName, ingest],
  );

  const send = useCallback(
    async (content: string) => {
      if (sending) return;
      setSending(true);
      try {
        await post(content);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: `failed_${Date.now()}`,
            sender: 'user',
            content,
            feedback: null,
            failed: { content },
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [sending, post],
  );

  const retry = useCallback(
    async (id: string) => {
      const failed = messagesRef.current.find((m) => m.id === id)?.failed;
      if (!failed || sending) return;
      setSending(true);
      try {
        await post(failed.content);
        setMessages((prev) => prev.filter((m) => m.id !== id));
      } catch {
        // keep the bubble; the user can retry again
      } finally {
        setSending(false);
      }
    },
    [sending, post],
  );

  const dismiss = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  return { messages, reply, loading, error, sending, send, retry, dismiss };
}
