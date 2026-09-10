import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

/** Building blocks the docs pages are written with. */

export function H2({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2
      id={id}
      className="mt-12 scroll-mt-8 border-b border-slate-200 pb-2 text-lg font-semibold tracking-tight text-slate-900 first:mt-0"
    >
      {children}
    </h2>
  );
}

export function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="mt-8 text-[15px] font-semibold text-slate-900">{children}</h3>;
}

export function P({ children }: { children: React.ReactNode }) {
  return <p className="mt-4 text-[15px] leading-7 text-slate-600">{children}</p>;
}

export function C({ children }: { children: React.ReactNode }) {
  return (
    <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[13px] text-slate-800">
      {children}
    </code>
  );
}

export function Note({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <div className="mt-5 rounded-r-lg border-l-2 border-indigo-400 bg-indigo-50/50 px-4 py-3">
      {title && <p className="text-sm font-semibold text-indigo-900">{title}</p>}
      <p className="text-sm leading-6 text-slate-600">{children}</p>
    </div>
  );
}

export function Snippet({ code, lang }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="mt-5 overflow-hidden rounded-lg bg-slate-900">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-2">
        <span className="font-mono text-xs text-slate-400">{lang ?? 'code'}</span>
        <button
          onClick={copy}
          className="flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium text-slate-400 transition hover:bg-white/10 hover:text-white"
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="overflow-x-auto px-4 py-3.5 text-[13px] leading-relaxed text-slate-100">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function Table({ head, rows }: { head: string[]; rows: React.ReactNode[][] }) {
  return (
    <div className="mt-5 overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr>
            {head.map((label) => (
              <th
                key={label}
                className="border-b border-slate-200 pb-2 pr-6 text-xs font-medium uppercase tracking-wide text-slate-400 last:pr-0"
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells, i) => (
            <tr key={i} className="align-top">
              {cells.map((cell, j) => (
                <td
                  key={j}
                  className="border-b border-slate-100 py-2.5 pr-6 leading-6 text-slate-600 last:pr-0"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
