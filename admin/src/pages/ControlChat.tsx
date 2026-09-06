import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Eye, Hand, Send, ThumbsUp, ThumbsDown } from 'lucide-react';
import Header from '../components/Header';
import { useMessages, useInterceptStream, sendAdminMessage, type Message } from '../api/sessions';

type Mode = 'audit' | 'intercept';

export default function ControlChat() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const mode: Mode = params.get('mode') === 'intercept' ? 'intercept' : 'audit';

  const { data, isLoading, error } = useMessages(id ?? '');
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');

  // Seed from the fetched transcript, then keep it live from the stream.
  useEffect(() => {
    if (data) setMessages(data);
  }, [data]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const lastId = messages[messages.length - 1]?.id;
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, lastId]);

  const ingest = useCallback((m: Message) => {
    setMessages((prev) => {
      const i = prev.findIndex((x) => x.id === m.id);
      if (i === -1) return [...prev, m];
      const next = prev.slice();
      next[i] = m;
      return next;
    });
  }, []);

  // Feedback-only update: touch just the vote on an existing message, leaving its
  // content and the list's length/order intact (so it doesn't trigger a scroll).
  const applyFeedback = useCallback((msgId: string, feedback: Message['feedback']) => {
    setMessages((prev) => {
      const i = prev.findIndex((x) => x.id === msgId);
      if (i === -1) return prev;
      const next = prev.slice();
      next[i] = { ...next[i], feedback };
      return next;
    });
  }, []);

  useInterceptStream(id ?? '', mode, { onMessage: ingest, onFeedback: applyFeedback });

  async function send() {
    const text = draft.trim();
    if (!text || !id) return;
    setDraft('');
    // The message is persisted + published, so it echoes back over the stream
    // and renders via ingest — no local optimistic append needed.
    try {
      await sendAdminMessage(id, text);
    } catch {
      // surface later
    }
  }

  return (
    <div className="flex h-screen flex-col">
      <Header
        right={
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
              mode === 'intercept'
                ? 'bg-amber-50 text-amber-700'
                : 'bg-slate-100 text-slate-600'
            }`}
          >
            {mode === 'intercept' ? <Hand size={14} /> : <Eye size={14} />}
            {mode === 'intercept' ? 'Intercepting' : 'Viewing'}
          </span>
        }
      >
        <button
          onClick={() => navigate('/control')}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
        >
          <ArrowLeft size={16} /> Sessions
        </button>
        <ChevronDivider />
        <h1 className="truncate font-mono text-sm font-semibold">{id}</h1>
      </Header>

      <div className="flex flex-1 flex-col overflow-y-auto bg-slate-50 px-6 py-6">
        {isLoading && (
          <div className="py-10 text-center text-sm text-slate-400">Loading messages…</div>
        )}
        {error && (
          <div className="py-10 text-center text-sm text-red-500">Failed to load messages.</div>
        )}
        {!isLoading && !error && messages.length === 0 && (
          <div className="py-10 text-center text-sm text-slate-400">No messages yet.</div>
        )}
        <div className="flex w-full flex-col gap-3">
          {messages.map((m) =>
            m.sender === 'system' ? (
              <div key={m.id} className="flex items-center gap-3 py-1">
                <div className="h-px flex-1 bg-slate-200" />
                <span className="text-xs text-slate-400">{m.content}</span>
                <div className="h-px flex-1 bg-slate-200" />
              </div>
            ) : (
              <div
                key={m.id}
                className={`flex flex-col ${m.sender === 'user' ? 'items-start' : 'items-end'}`}
              >
                <div
                  className={`max-w-lg rounded-2xl px-4 py-2 text-sm ${
                    m.sender === 'user'
                      ? 'rounded-bl-sm bg-white text-slate-800 shadow-sm'
                      : 'rounded-br-sm bg-indigo-600 text-white'
                  }`}
                >
                  {m.content}
                </div>
                {m.feedback && (
                  <span
                    className={`mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
                      m.feedback === 'like'
                        ? 'bg-green-50 text-green-700'
                        : 'bg-red-50 text-red-600'
                    }`}
                    title="User feedback on this reply"
                  >
                    {m.feedback === 'like' ? (
                      <ThumbsUp size={14} />
                    ) : (
                      <ThumbsDown size={14} />
                    )}
                    {m.feedback === 'like' ? 'Liked' : 'Disliked'}
                  </span>
                )}
              </div>
            )
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {mode === 'intercept' ? (
        <div className="border-t border-slate-200 bg-white px-6 py-4">
          <div className="flex items-end gap-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              rows={1}
              placeholder="Type a message to intervene…"
              className="max-h-40 min-h-[2.5rem] flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-indigo-400 focus:outline-none"
            />
            <button
              onClick={send}
              disabled={!draft.trim()}
              className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={16} /> Send
            </button>
          </div>
        </div>
      ) : (
        <div className="border-t border-slate-200 bg-white px-6 py-3 text-center text-xs text-slate-400">
          Read-only viewing mode. Switch to Intercept to send messages.
        </div>
      )}
    </div>
  );
}

function ChevronDivider() {
  return <span className="text-slate-300">›</span>;
}
