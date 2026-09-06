import { useEffect, useState } from 'react';

interface Props {
  children?: React.ReactNode;
  /** Replaces the default backend-health pill in the top-right slot. */
  right?: React.ReactNode;
}

export default function Header({ children, right }: Props) {
  const [health, setHealth] = useState<'checking' | 'ok' | 'down'>('checking');

  useEffect(() => {
    fetch('/health')
      .then((r) => r.json())
      .then((d) => setHealth(d.status === 'ok' ? 'ok' : 'down'))
      .catch(() => setHealth('down'));
  }, []);

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="flex items-center justify-between gap-4 px-6 py-3">
        <div className="flex min-w-0 items-center gap-3">{children}</div>
        {right ?? (
          <span
            className="flex items-center gap-1.5 text-xs font-medium text-slate-500"
            title={`backend: ${health}`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                health === 'ok'
                  ? 'bg-green-500'
                  : health === 'down'
                    ? 'bg-red-500'
                    : 'bg-amber-400'
              }`}
            />
            {health}
          </span>
        )}
      </div>
    </header>
  );
}
