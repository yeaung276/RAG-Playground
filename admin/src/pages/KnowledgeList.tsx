import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Check, Copy, Plus } from 'lucide-react';
import { useCreateKnowledgeBase, useKnowledgeBases } from '../api/knowledge';
import type { KnowledgeBaseConfig } from '../api/types';
import { formatDate } from '../utils/format';
import Header from '../components/Header';
import NewKbModal from '../components/NewKbModal';

export default function KnowledgeList() {
  const navigate = useNavigate();
  const { data: bases } = useKnowledgeBases();
  const createKnowledgeBase = useCreateKnowledgeBase();
  const [adding, setAdding] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  async function copyId(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    await navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId((c) => (c === id ? null : c)), 1500);
  }

  // Failures surface through the global toast handler in main.tsx.
  async function createBase(name: string, config: KnowledgeBaseConfig) {
    const kb = await createKnowledgeBase.mutateAsync({ name, config });
    navigate(`/knowledge/${kb.id}`);
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header>
        <BookOpen size={18} className="text-indigo-600" />
        <h1 className="truncate text-base font-semibold">Knowledge Service</h1>
      </Header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-sm font-medium text-slate-500">Your knowledge bases</h2>
          <button
            onClick={() => setAdding(true)}
            className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus size={16} /> New base
          </button>
        </div>

        {!bases && <p className="text-sm text-slate-400">Loading…</p>}

        {bases && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {bases.map((kb) => (
              <button
                key={kb.id}
                onClick={() => navigate(`/knowledge/${kb.id}`)}
                className="group flex flex-col items-start rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md"
              >
                <div className="mb-3 flex w-full items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                    <BookOpen size={20} />
                  </div>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => copyId(e, kb.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') copyId(e as unknown as React.MouseEvent, kb.id);
                    }}
                    title="Copy knowledge base ID"
                    className="flex max-w-[60%] items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-mono text-xs text-slate-500 hover:bg-slate-100"
                  >
                    <span className="truncate">{kb.id}</span>
                    {copiedId === kb.id ? (
                      <Check size={12} className="shrink-0 text-emerald-500" />
                    ) : (
                      <Copy size={12} className="shrink-0" />
                    )}
                  </span>
                </div>
                <span className="font-medium text-slate-900">{kb.name}</span>
                <span className="mt-1 text-xs text-slate-400">
                  {kb.fileCount} file{kb.fileCount === 1 ? '' : 's'} · {formatDate(kb.createdAt)}
                </span>
              </button>
            ))}

            <button
              onClick={() => setAdding(true)}
              className="flex min-h-[8rem] flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-200 text-slate-400 transition hover:border-indigo-300 hover:text-indigo-600"
            >
              <Plus size={22} />
              <span className="text-sm font-medium">New base</span>
            </button>
          </div>
        )}
      </main>

      <NewKbModal open={adding} onOpenChange={setAdding} onSubmit={createBase} />
    </div>
  );
}
