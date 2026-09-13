import { useEffect, useRef } from 'react';
import { useWidgetConfig } from '../config';
import { useChat } from '../hooks/useChat';
import ChatBubble from './ChatBubble';
import Composer from './Composer';

export default function ChatPanel() {
  const { agentName, welcomeMessage } = useWidgetConfig();
  const { messages, reply, loading, error, sending, send, retry, dismiss } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);
  const lastId = messages[messages.length - 1]?.id;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, lastId, reply?.content]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="flex min-h-full flex-col justify-end gap-3">
          <ChatBubble
            showFeedback={false}
            message={{
              id: 'welcome',
              sender: agentName,
              content: welcomeMessage,
              feedback: null,
            }}
          />

          {loading && (
            <div className="py-2 text-center text-xs text-gray-400">
              Loading messages…
            </div>
          )}
          {error && (
            <div className="py-2 text-center text-xs text-red-500">
              Failed to load messages.
            </div>
          )}

          {messages.map((message) => (
            <ChatBubble
              key={message.id}
              message={message}
              onRetry={retry}
              onDismiss={dismiss}
            />
          ))}

          {reply && (
            <ChatBubble
              streaming={{ tools: reply.tools }}
              message={{
                id: 'reply',
                sender: agentName,
                content: reply.content,
                  feedback: null,
              }}
            />
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <Composer onSend={send} disabled={sending} />
    </div>
  );
}
