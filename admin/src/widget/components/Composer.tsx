import { useRef, useState } from 'react';
import { Send } from 'lucide-react';

export interface ComposerProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export default function Composer({ onSend, disabled }: ComposerProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const content = value.trim();
    if (!content || disabled) return;
    setValue('');
    if (inputRef.current) inputRef.current.style.height = 'auto';
    onSend(content);
    inputRef.current?.focus();
  }

  return (
    <div className="shrink-0 border-t border-gray-200 p-3">
      <div className="flex items-end gap-2">
        <textarea
          ref={inputRef}
          rows={1}
          value={value}
          disabled={disabled}
          placeholder="Type a message…"
          onChange={(event) => {
            setValue(event.target.value);
            event.target.style.height = 'auto';
            event.target.style.height = `${Math.min(event.target.scrollHeight, 120)}px`;
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          className="max-h-30 flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-800 outline-none placeholder:text-gray-400 focus:border-indigo-400 disabled:bg-gray-50"
        />
        <button
          onClick={submit}
          disabled={disabled || value.trim() === ''}
          aria-label="Send"
          className="flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-full bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
}
