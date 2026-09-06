import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  SlidersHorizontal,
  ThumbsUp,
  ThumbsDown,
  ChevronLeft,
  ChevronRight,
  Eye,
  Hand,
  Copy,
  Check,
  CalendarRange,
  RefreshCw,
  X,
} from 'lucide-react';
import Header from '../components/Header';
import Tooltip from '../components/Tooltip';
import { formatDateTime, formatRelative } from '../utils/format';
import {
  useSessions,
  useAdminNotifications,
  type SessionScope,
  type SessionStatus,
  type SessionPriority,
} from '../api/sessions';

const PAGE_SIZE = 10;
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const TABS: { id: SessionScope; label: string }[] = [
  { id: 'current', label: 'Current' },
  { id: 'all', label: 'All chat session' },
];

const statusStyles: Record<SessionStatus, string> = {
  live: 'bg-green-50 text-green-700',
  away: 'bg-amber-50 text-amber-700',
};
const priorityStyles: Record<SessionPriority, string> = {
  urgent: 'bg-red-50 text-red-700',
  moderate: 'bg-amber-50 text-amber-700',
  low: 'bg-slate-100 text-slate-600',
};
function CopyId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(id);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      title={id}
      className="flex items-center gap-1.5 font-mono text-xs text-slate-700 hover:text-indigo-600"
    >
      {id.slice(0, 5)}…
      {copied ? (
        <Check size={13} className="text-green-600" />
      ) : (
        <Copy size={13} className="text-slate-400" />
      )}
    </button>
  );
}

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${className}`}
    >
      {label}
    </span>
  );
}

export default function ControlPanel() {
  const navigate = useNavigate();
  // Live: refetch the lists when the backend signals the attention list changed.
  useAdminNotifications();
  const [params, setParams] = useSearchParams();
  
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [now, setNow] = useState(() => Date.now());

  // Tab + page live in the URL so a refresh restores the view.
  const scope: SessionScope = params.get('tab') === 'all' ? 'all' : 'current';
  const page = Math.max(0, Number(params.get('page') ?? '1') - 1);
  const pageSize = PAGE_SIZE_OPTIONS.includes(Number(params.get('size')))
    ? Number(params.get('size'))
    : PAGE_SIZE;

  const range =
    scope === 'all'
      ? { from: from || undefined, to: to ? `${to}T23:59:59` : undefined }
      : {};
  const { data, dataUpdatedAt, isFetching, refetch } = useSessions(scope, page, pageSize, range);

  // Tick so the relative "updated Xs ago" label stays fresh between refetches.
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 15000);
    return () => clearInterval(t);
  }, []);

  function selectTab(id: SessionScope) {
    setFrom('');
    setTo('');
    setParams({ tab: id });
  }

  function goToPage(next: number) {
    const p = new URLSearchParams(params);
    p.set('page', String(next + 1));
    setParams(p);
  }

  function setPageSize(next: number) {
    const p = new URLSearchParams(params);
    p.set('size', String(next));
    p.set('page', '1');
    setParams(p);
  }

  function setRange(next: { from?: string; to?: string }) {
    if (next.from !== undefined) setFrom(next.from);
    if (next.to !== undefined) setTo(next.to);
    goToPage(0);
  }

  // Priority is only meaningful for live triage; hide it in the history tab.
  const showPriority = scope === 'current';
  const rows = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : page * pageSize + 1;
  const end = Math.min((page + 1) * pageSize, total);

  return (
    <div className="min-h-screen">
      <Header>
        <SlidersHorizontal size={18} className="text-indigo-600" />
        <h1 className="truncate text-base font-semibold">Control Panel</h1>
      </Header>

      <main className="px-6 py-8">
        <div className="mb-5 flex items-center justify-between border-b border-slate-200">
          <div className="flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => selectTab(tab.id)}
                className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
                  scope === tab.id
                    ? 'border-indigo-600 text-indigo-700'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <button
            onClick={() => refetch()}
            title="Refresh"
            className="mb-1 flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
            {dataUpdatedAt ? `Updated ${formatRelative(dataUpdatedAt, now)}` : 'Refresh'}
          </button>
        </div>

        {scope === 'all' && (
          <div className="mb-4 flex justify-end">
            <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm">
              <CalendarRange size={16} className="text-slate-400" />
              <input
                type="date"
                value={from}
                max={to || undefined}
                onChange={(e) => setRange({ from: e.target.value })}
                className="bg-transparent text-slate-700 focus:outline-none"
              />
              <span className="text-slate-300">–</span>
              <input
                type="date"
                value={to}
                min={from || undefined}
                onChange={(e) => setRange({ to: e.target.value })}
                className="bg-transparent text-slate-700 focus:outline-none"
              />
              {(from || to) && (
                <button
                  onClick={() => setRange({ from: '', to: '' })}
                  title="Clear filter"
                  className="ml-1 rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                >
                  <X size={15} />
                </button>
              )}
            </div>
          </div>
        )}

        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-medium uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">Session ID</th>
                  <th className="px-4 py-3">Status</th>
                  {showPriority && <th className="px-4 py-3">Priority</th>}
                  <th className="px-4 py-3">Trigger Message</th>
                  <th className="px-4 py-3">Votes</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr
                    key={s.id}
                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
                  >
                    <td className="px-4 py-3">
                      <CopyId id={s.id} />
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        label={s.status === 'live' ? 'Live' : 'Away'}
                        className={statusStyles[s.status]}
                      />
                    </td>
                    {showPriority && (
                      <td className="px-4 py-3">
                        <Badge
                          label={s.priority[0].toUpperCase() + s.priority.slice(1)}
                          className={priorityStyles[s.priority]}
                        />
                      </td>
                    )}
                    <td className="px-4 py-3 text-slate-600">
                      <Tooltip content={s.triggerMessage} className="max-w-[16rem] truncate">
                        {s.triggerMessage}
                      </Tooltip>
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-3 text-xs text-slate-600">
                        <span className="flex items-center gap-1">
                          <ThumbsUp size={13} className="text-green-600" />
                          {s.upvotes}
                        </span>
                        <span className="flex items-center gap-1">
                          <ThumbsDown size={13} className="text-red-500" />
                          {s.downvotes}
                        </span>
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-500">
                      {formatDateTime(s.createdAt)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => navigate(`/control/${s.id}?mode=audit`)}
                          className="flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                        >
                          <Eye size={14} /> View
                        </button>
                        {scope === 'current' && (
                          <button
                            onClick={() => navigate(`/control/${s.id}?mode=intercept`)}
                            className="flex items-center gap-1 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100"
                          >
                            <Hand size={14} /> Intercept
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}

                {rows.length === 0 && (
                  <tr>
                    <td colSpan={showPriority ? 7 : 6} className="px-4 py-10 text-center text-slate-400">
                      No sessions.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 text-sm text-slate-500">
            <div className="flex items-center gap-3">
              <span>
                {start}–{end} of {total}
              </span>
              <label className="flex items-center gap-1">
                <span className="text-xs">Rows per page</span>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value))}
                  className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600"
                >
                  {PAGE_SIZE_OPTIONS.map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => goToPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronLeft size={16} /> Prev
              </button>
              <span className="px-2 text-xs">
                Page {page + 1} of {pageCount}
              </span>
              <button
                onClick={() => goToPage(Math.min(pageCount - 1, page + 1))}
                disabled={page >= pageCount - 1}
                className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
