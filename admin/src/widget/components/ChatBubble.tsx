import { useState } from 'react';
import { ChevronRight, RotateCw, ThumbsDown, ThumbsUp, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useWidgetConfig } from '../config';
import { useFeedback } from '../hooks/useFeedback';
import type { ChatMessage, Feedback } from '../hooks/useChat';

const IMAGE_NOTE = '🖼️ Image attached';

function Avatar() {
  const { iconUrl, agentName } = useWidgetConfig();
  return iconUrl ? (
    <img src={iconUrl} alt="" className="mt-0.5 size-7 shrink-0 rounded-full object-cover" />
  ) : (
    <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-indigo-500 text-xs font-medium text-white">
      {agentName.trim().charAt(0).toUpperCase()}
    </span>
  );
}

function ToolCalls({ tools }: { tools: string[] }) {
  const [open, setOpen] = useState(false);
  if (tools.length === 0) return null;

  return (
    <div className="mb-1 overflow-hidden rounded-xl border border-gray-200 bg-white text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full cursor-pointer items-center gap-1.5 px-2.5 py-1.5 text-left text-gray-600"
      >
        <ChevronRight
          size={12}
          className={`shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <span className="size-1.5 shrink-0 animate-pulse rounded-full bg-indigo-500" />
        <span className="truncate">{tools[tools.length - 1]}</span>
      </button>
      {open && (
        <ul className="border-t border-gray-200 px-2.5 py-1.5 text-gray-500">
          {tools.map((tool, i) => (
            <li key={i} className="truncate py-0.5">
              {tool}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function TypingDots() {
  return (
    <span className="flex gap-1 py-1">
      {[0, 0.15, 0.3].map((delay) => (
        <span
          key={delay}
          className="size-1.5 animate-pulse rounded-full bg-gray-400"
          style={{ animationDelay: `${delay}s` }}
        />
      ))}
    </span>
  );
}

function Vote({ message }: { message: ChatMessage }) {
  const [vote, setVote] = useState(message.feedback);
  const { isSubmitting, submit } = useFeedback(message.id);

  async function cast(value: Feedback) {
    const previous = vote;
    const next = vote === value ? null : value;
    setVote(next);
    if (!(await submit(next))) setVote(previous);
  }

  const style = (active: boolean, on: string) =>
    `flex cursor-pointer items-center rounded-full border p-1.5 transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
      active ? on : 'border-gray-200 text-gray-400 hover:bg-gray-100'
    }`;

  return (
    <div className="mt-1 flex gap-1">
      <button
        onClick={() => cast('like')}
        disabled={isSubmitting}
        aria-pressed={vote === 'like'}
        aria-label="Like this reply"
        className={style(vote === 'like', 'border-green-200 bg-green-50 text-green-600')}
      >
        <ThumbsUp size={13} />
      </button>
      <button
        onClick={() => cast('dislike')}
        disabled={isSubmitting}
        aria-pressed={vote === 'dislike'}
        aria-label="Dislike this reply"
        className={style(vote === 'dislike', 'border-red-200 bg-red-50 text-red-500')}
      >
        <ThumbsDown size={13} />
      </button>
    </div>
  );
}

export interface ChatBubbleProps {
  message: ChatMessage;
  streaming?: { tools: string[] };
  showFeedback?: boolean;
  onRetry?: (id: string) => void;
  onDismiss?: (id: string) => void;
}

export default function ChatBubble({
  message,
  streaming,
  showFeedback = true,
  onRetry,
  onDismiss,
}: ChatBubbleProps) {
  if (message.sender === 'system') {
    return (
      <div className="flex items-center gap-3 py-1">
        <span className="h-px flex-1 bg-gray-200" />
        <span className="text-xs text-gray-400">{message.content}</span>
        <span className="h-px flex-1 bg-gray-200" />
      </div>
    );
  }

  if (message.sender === 'user') {
    const failed = message.failed !== undefined;
    return (
      <div className="flex flex-col items-end">
        <div
          className={`max-w-[85%] rounded-2xl rounded-br-sm px-3 py-2 text-sm whitespace-pre-wrap ${
            failed ? 'bg-red-50 text-red-900 ring-1 ring-red-200' : 'bg-indigo-600 text-white'
          }`}
        >
          {message.content}
          {message.hasImage && (
            <div className="mt-1 text-xs opacity-80">{IMAGE_NOTE}</div>
          )}
        </div>
        {failed && (
          <div className="mt-1 flex items-center gap-2 text-xs text-red-600">
            <span>Not sent</span>
            <button
              onClick={() => onRetry?.(message.id)}
              className="flex cursor-pointer items-center gap-1 rounded-full border border-red-200 px-2 py-0.5 font-medium hover:bg-red-50"
            >
              <RotateCw size={11} /> Retry
            </button>
            <button
              onClick={() => onDismiss?.(message.id)}
              aria-label="Dismiss"
              className="cursor-pointer rounded-full p-0.5 text-red-400 hover:bg-red-50"
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <Avatar />
      <div className="min-w-0 flex-1">
        {streaming && <ToolCalls tools={streaming.tools} />}
        <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-gray-100 px-3 py-2 text-sm text-gray-800">
          {message.content ? (
            <div className="wg-md">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          ) : (
            <TypingDots />
          )}
          {message.hasImage && (
            <div className="mt-1 text-xs text-gray-500">{IMAGE_NOTE}</div>
          )}
        </div>
        {!streaming && showFeedback && <Vote message={message} />}
      </div>
    </div>
  );
}
