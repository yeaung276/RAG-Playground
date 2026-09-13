import { useEffect, useRef, useState } from 'react';
import {
  ArrowRightLeft,
  ChevronRight,
  Loader2,
  Send,
  Sparkles,
  User,
  Wrench,
} from 'lucide-react';
import { streamAgentTest, type TestFrame } from '../api/agents';
import { errorMessage } from '../api/client';

// A throwaway test run: everything here lives in local state, so unmounting
// the component drops it. The thread id is what the checkpointer resumes from,
// and both panes are views over the frames the run streamed back — left shows
// what a user would see, right shows every message including tool calls.

type TraceFrame = Extract<TestFrame, { type: 'message' | 'tool_result' | 'tool_call' }>;

export default function AgentTrace() {
  const [frames, setFrames] = useState<TraceFrame[]>([]);
  const [thinking, setThinking] = useState('');
  const [answer, setAnswer] = useState('');
  const [calling, setCalling] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const threadId = useRef(crypto.randomUUID());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [frames.length, answer, thinking]);

  async function send() {
    const text = input.trim();
    if (!text || running) return;
    setInput('');
    setError(null);
    setThinking('');
    setAnswer('');
    setRunning(true);
    setFrames((prev) => [
      ...prev,
      { type: 'message', agent: null, role: 'human', content: text, thinking: null, usage: null },
    ]);

    try {
      await streamAgentTest(threadId.current, text, (frame) => {
        switch (frame.type) {
          case 'thinking':
            setThinking((prev) => prev + frame.delta);
            break;
          case 'token':
            setAnswer((prev) => prev + frame.delta);
            break;
          case 'tool_call':
            setCalling(frame.name);
            setFrames((prev) => [...prev, frame]);
            break;
          case 'tool_result':
            setCalling(null);
            setFrames((prev) => [...prev, frame]);
            break;
          case 'message':
            setThinking('');
            setAnswer('');
            setFrames((prev) => [...prev, frame]);
            break;
          case 'error':
            setError(frame.message);
            break;
        }
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning(false);
      setCalling(null);
      setThinking('');
      setAnswer('');
    }
  }

  function clear() {
    threadId.current = crypto.randomUUID();
    setFrames([]);
    setThinking('');
    setAnswer('');
    setError(null);
  }

  return (
    <div className="flex min-h-0 flex-1">
      <Conversation
        frames={frames}
        thinking={thinking}
        answer={answer}
        calling={calling}
        running={running}
        error={error}
        input={input}
        onInput={setInput}
        onSend={send}
        bottomRef={bottomRef}
      />
      <TracePane frames={frames} onClear={clear} />
    </div>
  );
}

/** Left pane: only what a user would have seen — spoken turns, no plumbing. */
function Conversation({
  frames,
  thinking,
  answer,
  calling,
  running,
  error,
  input,
  onInput,
  onSend,
  bottomRef,
}: {
  frames: TraceFrame[];
  thinking: string;
  answer: string;
  calling: string | null;
  running: boolean;
  error: string | null;
  input: string;
  onInput: (value: string) => void;
  onSend: () => void;
  bottomRef: React.RefObject<HTMLDivElement>;
}) {
  const spoken = frames.filter(
    (f): f is Extract<TraceFrame, { type: 'message' }> =>
      f.type === 'message' && f.content.trim().length > 0,
  );

  return (
    <section className="flex min-w-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {!spoken.length && !running ? (
          <p className="pt-10 text-center text-sm text-slate-400">
            Send a message to start the flow.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {spoken.map((f, i) => (
              <Bubble key={i} frame={f} />
            ))}
            {running && <Live thinking={thinking} answer={answer} calling={calling} />}
            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="flex items-end gap-2 border-t border-slate-200 px-5 py-3">
        <textarea
          rows={1}
          value={input}
          onChange={(e) => onInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder="Ask the agent something…"
          className="max-h-32 min-h-[38px] flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
        <button
          onClick={onSend}
          disabled={!input.trim() || running}
          className="flex h-[38px] shrink-0 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Send size={15} />
          Send
        </button>
      </div>
    </section>
  );
}

/** The turn in flight: a spinner, whatever it is thinking, then its tokens. */
function Live({
  thinking,
  answer,
  calling,
}: {
  thinking: string;
  answer: string;
  calling: string | null;
}) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        <span className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
          <Loader2 size={12} className="animate-spin" />
          {calling ? `Calling ${calling}…` : 'Thinking…'}
        </span>
        {thinking && (
          <p className="mb-1.5 max-h-24 overflow-y-auto whitespace-pre-wrap border-l-2 border-slate-200 pl-2 text-xs italic text-slate-400">
            {thinking}
          </p>
        )}
        {answer && (
          <div className="whitespace-pre-wrap rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-800">
            {answer}
          </div>
        )}
      </div>
    </div>
  );
}

function Bubble({ frame }: { frame: Extract<TraceFrame, { type: 'message' }> }) {
  const mine = frame.role === 'human';
  return (
    <div className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[80%]">
        {frame.agent && !mine && (
          <span className="mb-1 block text-[11px] font-medium text-slate-400">{frame.agent}</span>
        )}
        <div
          className={`whitespace-pre-wrap rounded-xl px-3 py-2 text-sm ${
            mine ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-800'
          }`}
        >
          {frame.content}
        </div>
      </div>
    </div>
  );
}

/** Right pane: every frame in order, tool results broken out of the turns. */
function TracePane({ frames, onClear }: { frames: TraceFrame[]; onClear: () => void }) {
  return (
    <aside className="flex w-[46%] min-w-0 shrink-0 flex-col border-l border-slate-200 bg-slate-50">
      <div className="flex items-center justify-between border-b border-slate-200 px-4 py-2.5">
        <h3 className="text-sm font-semibold text-slate-700">
          Trace <span className="font-normal text-slate-400">· {frames.length} frames</span>
        </h3>
        <button
          onClick={onClear}
          disabled={!frames.length}
          className="text-xs font-medium text-slate-500 hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Clear
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {frames.length === 0 ? (
          <p className="pt-10 text-center text-sm text-slate-400">
            LLM turns, tool calls and their results appear here as they happen.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {frames.map((f, i) => (
              <TraceRow key={i} frame={f} />
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

function TraceRow({ frame }: { frame: TraceFrame }) {
  const [open, setOpen] = useState(false);
  const handoff = frame.type !== 'message' && (frame.name ?? '').startsWith('transfer_to_');
  const Icon = handoff
    ? ArrowRightLeft
    : frame.type === 'tool_result'
      ? Wrench
      : frame.type === 'tool_call'
        ? Loader2
        : frame.role === 'ai'
          ? Sparkles
          : User;

  const tone = handoff
    ? 'bg-sky-50 text-sky-700'
    : frame.type === 'tool_result' || frame.type === 'tool_call'
      ? 'bg-amber-50 text-amber-700'
      : frame.role === 'ai'
        ? 'bg-indigo-50 text-indigo-700'
        : 'bg-slate-100 text-slate-600';

  const title =
    frame.type === 'message' ? frame.content || 'response' : (frame.name ?? 'tool');

  return (
    <li className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-slate-50"
      >
        <ChevronRight
          size={14}
          className={`shrink-0 text-slate-400 transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <span
          className={`flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 font-mono text-[11px] font-medium ${tone}`}
        >
          <Icon size={11} />
          {frame.type}
        </span>
        <span className="min-w-0 flex-1 truncate text-sm text-slate-800">{title}</span>
        {frame.type !== 'tool_call' && frame.agent && (
          <span className="shrink-0 text-[11px] text-slate-400">{frame.agent}</span>
        )}
        {frame.type === 'tool_result' && (
          <>
            {frame.elapsedMs !== null && (
              <span className="shrink-0 font-mono text-[11px] text-slate-400">
                {frame.elapsedMs}ms
              </span>
            )}
            <span
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                frame.status === 'error' ? 'bg-red-500' : 'bg-green-500'
              }`}
              title={frame.status}
            />
          </>
        )}
      </button>

      {open && (
        <div className="border-t border-slate-100 px-3 py-2">
          {frame.type === 'tool_result' && (
            <>
              <Payload label="args" body={JSON.stringify(frame.args, null, 2)} />
              <Payload label="result" body={frame.content || '(empty)'} />
            </>
          )}
          {frame.type === 'message' && (
            <>
              {frame.thinking && <Payload label="thinking" body={frame.thinking} />}
              <Payload label="content" body={frame.content || '(empty)'} />
              {frame.usage && (
                <Payload label="usage" body={JSON.stringify(frame.usage, null, 2)} />
              )}
            </>
          )}
        </div>
      )}
    </li>
  );
}

function Payload({ label, body }: { label: string; body: string }) {
  return (
    <div className="mt-1.5 first:mt-0">
      <span className="font-mono text-[11px] font-medium text-slate-400">{label}</span>
      <pre className="mt-1 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded bg-slate-50 px-2 py-1.5 font-mono text-[12px] leading-relaxed text-slate-700">
        {body}
      </pre>
    </div>
  );
}
