import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useParams } from 'react-router-dom';
import { ChevronDown, ChevronLeft, ChevronRight, FileText } from 'lucide-react';
import { SECTIONS } from './sections';

const GROUPS = [...new Set(SECTIONS.map((s) => s.group))];

export default function Docs() {
  const { section } = useParams();
  const active = SECTIONS.find((s) => s.slug === section) ?? SECTIONS[0];
  const Body = active.body;

  const [collapsed, setCollapsed] = useState<string[]>([]);
  const article = useRef<HTMLElement>(null);
  const [toc, setToc] = useState<{ id: string; text: string }[]>([]);

  useEffect(() => {
    const headings = article.current?.querySelectorAll<HTMLHeadingElement>('h2[id]') ?? [];
    setToc([...headings].map((h) => ({ id: h.id, text: h.textContent ?? '' })));
  }, [active.slug]);

  function toggle(group: string) {
    setCollapsed((open) =>
      open.includes(group) ? open.filter((g) => g !== group) : [...open, group],
    );
  }

  // Anchor hrefs would be swallowed by the hash router, so scroll by hand.
  function jump(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <div className="flex h-screen bg-white text-slate-900">
      <aside className="flex w-60 shrink-0 flex-col overflow-y-auto border-r border-slate-200 px-4 py-5">
        <Link
          to="/control"
          className="flex items-center gap-1 px-2 text-xs font-medium text-slate-400 transition hover:text-slate-700"
        >
          <ChevronLeft size={13} /> Console
        </Link>
        <div className="mt-3 flex items-center gap-2 px-2">
          <FileText size={17} className="text-indigo-600" />
          <span className="text-base font-semibold tracking-tight">Docs</span>
        </div>

        <nav className="mt-6 flex flex-col gap-4">
          {GROUPS.map((group) => (
            <div key={group}>
              <button
                onClick={() => toggle(group)}
                className="flex w-full items-center gap-1 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400 transition hover:text-slate-600"
              >
                {collapsed.includes(group) ? (
                  <ChevronRight size={12} />
                ) : (
                  <ChevronDown size={12} />
                )}
                {group}
              </button>
              {!collapsed.includes(group) && (
                <div className="mt-1 flex flex-col border-l border-slate-200">
                  {SECTIONS.filter((s) => s.group === group).map((s) => (
                    <NavLink
                      key={s.slug}
                      to={`/docs/${s.slug}`}
                      className={({ isActive }) =>
                        `-ml-px border-l py-1.5 pl-4 text-sm transition ${
                          isActive
                            ? 'border-indigo-600 font-medium text-indigo-700'
                            : 'border-transparent text-slate-600 hover:border-slate-300 hover:text-slate-900'
                        }`
                      }
                    >
                      {s.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>
      </aside>

      <div className="min-w-0 flex-1 overflow-auto">
        <div className="mx-auto flex max-w-4xl gap-12 px-10 py-10">
          <article ref={article} className="min-w-0 max-w-2xl flex-1">
            <p className="text-xs font-medium uppercase tracking-wide text-indigo-600">
              {active.group}
            </p>
            <h1 className="mt-1 mb-8 text-3xl font-semibold tracking-tight">{active.label}</h1>
            <Body />
          </article>

          <aside className="sticky top-0 hidden w-40 shrink-0 self-start xl:block">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              On this page
            </p>
            <ul className="mt-2 flex flex-col border-l border-slate-200">
              {toc.map(({ id, text }) => (
                <li key={id} className="flex">
                  <button
                    onClick={() => jump(id)}
                    className="-ml-px border-l border-transparent py-1 pl-3 text-left text-sm text-slate-500 transition hover:border-indigo-500 hover:text-indigo-700"
                  >
                    {text}
                  </button>
                </li>
              ))}
            </ul>
          </aside>
        </div>
      </div>
    </div>
  );
}
