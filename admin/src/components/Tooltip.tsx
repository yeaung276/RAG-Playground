import { useState, type ReactNode } from 'react';

/** Lightweight hover tooltip. Uses fixed positioning so it isn't clipped by the
 * table's overflow containers (a CSS group-hover bubble would be). `className`
 * styles the trigger element (e.g. truncation). */
export default function Tooltip({
  content,
  className,
  children,
}: {
  content: string;
  className?: string;
  children: ReactNode;
}) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

  if (!content) return <div className={className}>{children}</div>;

  return (
    <>
      <div
        className={className}
        onMouseEnter={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setPos({ x: r.left + r.width / 2, y: r.bottom });
        }}
        onMouseLeave={() => setPos(null)}
      >
        {children}
      </div>
      {pos && (
        <div
          style={{ left: pos.x, top: pos.y + 8 }}
          className="pointer-events-none fixed z-50 max-w-md -translate-x-1/2 whitespace-pre-wrap break-words rounded-md bg-slate-800 px-2.5 py-1.5 text-xs text-white shadow-lg"
        >
          {content}
        </div>
      )}
    </>
  );
}
