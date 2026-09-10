import { useState } from 'react';
import {
  Braces,
  ChevronDown,
  ChevronRight,
  Globe,
  KeyRound,
  Play,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import { useTestTool } from '../api/agents';
import { errorMessage } from '../api/client';
import { uid, type Agent, type Param, type Tool } from '../types/agent';

interface Props {
  agent: Agent;
  onEdit: (patch: Partial<Agent>) => void;
}

export default function AgentTools({ agent, onEdit }: Props) {
  const [openToolId, setOpenToolId] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, string>>({});
  // Param values live only in this panel — they are test input, not config.
  const [values, setValues] = useState<Record<string, Record<string, string>>>({});
  const testTool_ = useTestTool();

  function editTool(toolId: string, patch: Partial<Tool>) {
    onEdit({ tools: agent.tools.map((t) => (t.id === toolId ? { ...t, ...patch } : t)) });
  }

  // After a reload the token field is blank because the token itself stays on
  // the server, so report where the credential would come from, not its value.
  function credentialSource(t: Tool): string {
    if (t.auth === 'none') return 'none';
    if (t.auth === 'basic') return t.authPass ? 'from this form' : 'not set';
    if (t.authToken) return 'from this form';
    return t.hasAuthToken ? 'stored on the server' : 'not set';
  }

  // Sends the tool as edited — the server runs it, saved or not, and falls back
  // to the stored token when the field is blank.
  function testTool(t: Tool) {
    setTesting(t.id);
    setResults((r) => ({ ...r, [t.id]: '' }));
    const { id, hasAuthToken, saved, authToken, ...rest } = t;
    testTool_.mutate(
      {
        agentId: agent.id,
        tool: { ...rest, ...(authToken ? { authToken } : {}) },
        params: values[t.id] ?? {},
      },
      {
        onSuccess: (res) =>
          setResults((r) => ({
            ...r,
            [t.id]: JSON.stringify(
              {
                sent: { ...res.request, credential: credentialSource(t) },
                status: res.status,
                elapsedMs: res.elapsedMs,
                error: res.error,
                body: res.body,
              },
              null,
              2,
            ),
          })),
        onError: (err) => setResults((r) => ({ ...r, [t.id]: errorMessage(err) })),
        onSettled: () => setTesting(null),
      },
    );
  }

  return (
    <div className="max-w-3xl space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            HTTP tools
          </p>
          <p className="mt-0.5 text-[11px] text-slate-400">
            Each tool is one HTTP request. Reference a parameter anywhere in the URL,
            query, headers or body as{' '}
            <code className="rounded bg-slate-100 px-1">{'{{name}}'}</code>.
          </p>
        </div>
        <button
          onClick={() => {
            const id = uid();
            onEdit({
              tools: [
                ...agent.tools,
                {
                  id,
                  name: 'new_tool',
                  description: '',
                  enabled: true,
                  method: 'GET',
                  url: 'https://',
                  headers: [],
                  query: [],
                  body: '',
                  auth: 'none',
                  authToken: '',
                  authHeader: '',
                  authUser: '',
                  authPass: '',
                  timeoutMs: 8000,
                  params: [],
                  hasAuthToken: false,
                  saved: false,
                },
              ],
            });
            setOpenToolId(id);
          }}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus size={15} /> Add tool
        </button>
      </div>

      {agent.tools.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-200 px-4 py-8 text-center text-sm text-slate-400">
          No tools yet. Add one to let this agent call an HTTP API.
        </p>
      )}

      {agent.tools.map((t) => (
        <div key={t.id} className="overflow-hidden rounded-xl border border-slate-200">
          <div className="flex items-center gap-2.5 px-3 py-2.5">
            <button
              onClick={() => setOpenToolId(openToolId === t.id ? null : t.id)}
              className="shrink-0 text-slate-400 hover:text-slate-600"
            >
              {openToolId === t.id ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )}
            </button>
            <span
              className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                t.method === 'GET'
                  ? 'bg-emerald-50 text-emerald-700'
                  : t.method === 'DELETE'
                    ? 'bg-red-50 text-red-700'
                    : t.method === 'POST'
                      ? 'bg-indigo-50 text-indigo-700'
                      : 'bg-amber-50 text-amber-700'
              }`}
            >
              {t.method}
            </span>
            <button
              onClick={() => setOpenToolId(openToolId === t.id ? null : t.id)}
              className="min-w-0 flex-1 text-left"
            >
              <span className="block truncate font-mono text-sm font-medium text-slate-800">
                {t.name || '(unnamed)'}
              </span>
              <span className="block truncate text-[11px] text-slate-400">
                {t.url || 'No URL'}
              </span>
            </button>
            <label
              title={t.enabled ? 'Enabled' : 'Disabled'}
              className="flex shrink-0 items-center gap-1.5 text-[11px] text-slate-500"
            >
              <input
                type="checkbox"
                checked={t.enabled}
                onChange={(e) => editTool(t.id, { enabled: e.target.checked })}
                className="h-3.5 w-3.5 accent-indigo-600"
              />
              {t.enabled ? 'On' : 'Off'}
            </label>
            <button
              onClick={() =>
                onEdit({ tools: agent.tools.filter((x) => x.id !== t.id) })
              }
              title="Remove tool"
              className="shrink-0 rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
            >
              <Trash2 size={15} />
            </button>
          </div>

          {openToolId === t.id && (
            <div className="space-y-5 border-t border-slate-200 bg-slate-50/60 px-4 py-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block">
                  <span className="text-xs font-medium text-slate-500">Tool name</span>
                  <input
                    value={t.name}
                    readOnly={t.saved}
                    disabled={t.saved}
                    title={t.saved ? 'Fixed once saved — delete and re-add to rename' : undefined}
                    onChange={(e) => editTool(t.id, { name: e.target.value })}
                    placeholder="lookup_order"
                    className={`mt-1 w-full rounded-lg border px-3 py-2 font-mono text-sm outline-none focus:ring-1 ${
                      t.name.trim()
                        ? 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500'
                        : 'border-red-400 focus:border-red-500 focus:ring-red-500'
                    }`}
                  />
                  <span className="mt-0.5 block text-[10px] text-slate-400">
                    snake_case. This is the function name the model calls.
                  </span>
                </label>
                <label className="block">
                  <span className="text-xs font-medium text-slate-500">
                    Timeout (ms)
                  </span>
                  <input
                    type="number"
                    min={100}
                    value={t.timeoutMs}
                    onChange={(e) =>
                      editTool(t.id, { timeoutMs: Number(e.target.value) })
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </label>
              </div>

              <label className="block">
                <span className="text-xs font-medium text-slate-500">Description</span>
                <textarea
                  value={t.description}
                  onChange={(e) => editTool(t.id, { description: e.target.value })}
                  rows={2}
                  placeholder="What this tool does and when the model should call it."
                  className="mt-1 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </label>

              <div>
                <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <Globe size={12} /> Request
                </p>
                <div className="flex gap-2">
                  <select
                    value={t.method}
                    onChange={(e) =>
                      editTool(t.id, { method: e.target.value as Tool['method'] })
                    }
                    className="w-28 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="PATCH">PATCH</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                  <input
                    value={t.url}
                    onChange={(e) => editTool(t.id, { url: e.target.value })}
                    placeholder="https://api.example.com/v1/orders/{{order_id}}"
                    className={`min-w-0 flex-1 rounded-lg border px-3 py-2 font-mono text-sm outline-none focus:ring-1 ${
                      /^https?:\/\/.+/.test(t.url)
                        ? 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500'
                        : 'border-red-400 focus:border-red-500 focus:ring-red-500'
                    }`}
                  />
                </div>
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Query parameters
                  </p>
                  <button
                    onClick={() =>
                      editTool(t.id, {
                        query: [...t.query, { id: uid(), key: '', value: '' }],
                      })
                    }
                    className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium text-indigo-600 hover:bg-indigo-50"
                  >
                    <Plus size={12} /> Add
                  </button>
                </div>
                {t.query.length === 0 && (
                  <p className="text-[11px] text-slate-400">None.</p>
                )}
                <div className="space-y-1.5">
                  {t.query.map((q) => (
                    <div key={q.id} className="flex gap-2">
                      <input
                        value={q.key}
                        onChange={(e) =>
                          editTool(t.id, {
                            query: t.query.map((x) =>
                              x.id === q.id ? { ...x, key: e.target.value } : x,
                            ),
                          })
                        }
                        placeholder="province"
                        className="w-44 shrink-0 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                      <input
                        value={q.value}
                        onChange={(e) =>
                          editTool(t.id, {
                            query: t.query.map((x) =>
                              x.id === q.id ? { ...x, value: e.target.value } : x,
                            ),
                          })
                        }
                        placeholder="{{province}}"
                        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                      <button
                        onClick={() =>
                          editTool(t.id, {
                            query: t.query.filter((x) => x.id !== q.id),
                          })
                        }
                        className="shrink-0 rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Headers
                  </p>
                  <button
                    onClick={() =>
                      editTool(t.id, {
                        headers: [...t.headers, { id: uid(), key: '', value: '' }],
                      })
                    }
                    className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium text-indigo-600 hover:bg-indigo-50"
                  >
                    <Plus size={12} /> Add
                  </button>
                </div>
                {t.headers.length === 0 && (
                  <p className="text-[11px] text-slate-400">None.</p>
                )}
                <div className="space-y-1.5">
                  {t.headers.map((h) => (
                    <div key={h.id} className="flex gap-2">
                      <input
                        value={h.key}
                        onChange={(e) =>
                          editTool(t.id, {
                            headers: t.headers.map((x) =>
                              x.id === h.id ? { ...x, key: e.target.value } : x,
                            ),
                          })
                        }
                        placeholder="Accept"
                        className="w-44 shrink-0 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                      <input
                        value={h.value}
                        onChange={(e) =>
                          editTool(t.id, {
                            headers: t.headers.map((x) =>
                              x.id === h.id ? { ...x, value: e.target.value } : x,
                            ),
                          })
                        }
                        placeholder="application/json"
                        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                      <button
                        onClick={() =>
                          editTool(t.id, {
                            headers: t.headers.filter((x) => x.id !== h.id),
                          })
                        }
                        className="shrink-0 rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {t.method !== 'GET' && t.method !== 'DELETE' && (
                <label className="block">
                  <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    <Braces size={12} /> Body template
                  </span>
                  <textarea
                    value={t.body}
                    onChange={(e) => editTool(t.id, { body: e.target.value })}
                    rows={5}
                    spellCheck={false}
                    placeholder={'{\n  "orderId": "{{order_id}}"\n}'}
                    className="mt-1 w-full resize-y rounded-lg border border-slate-300 px-3 py-2 font-mono text-[12px] outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </label>
              )}

              <div>
                <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  <KeyRound size={12} /> Authentication
                </p>
                <div className="flex flex-wrap items-start gap-2">
                  <select
                    value={t.auth}
                    onChange={(e) =>
                      editTool(t.id, { auth: e.target.value as Tool['auth'] })
                    }
                    className="w-40 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="none">None</option>
                    <option value="bearer">Bearer token</option>
                    <option value="header">API key header</option>
                    <option value="basic">Basic auth</option>
                  </select>

                  {t.auth === 'bearer' && (
                    <input
                      type="password"
                      value={t.authToken}
                      onChange={(e) => editTool(t.id, { authToken: e.target.value })}
                      placeholder={t.hasAuthToken ? 'Stored — leave blank to keep' : 'Token'}
                      className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  )}

                  {t.auth === 'header' && (
                    <>
                      <input
                        value={t.authHeader}
                        onChange={(e) =>
                          editTool(t.id, { authHeader: e.target.value })
                        }
                        placeholder="X-Api-Key"
                        className="w-40 shrink-0 rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                      <input
                        type="password"
                        value={t.authToken}
                        onChange={(e) =>
                          editTool(t.id, { authToken: e.target.value })
                        }
                        placeholder={t.hasAuthToken ? 'Stored — leave blank to keep' : 'Key'}
                        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                    </>
                  )}

                  {t.auth === 'basic' && (
                    <>
                      <input
                        value={t.authUser}
                        onChange={(e) => editTool(t.id, { authUser: e.target.value })}
                        placeholder="Username"
                        className="w-40 shrink-0 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                      <input
                        type="password"
                        value={t.authPass}
                        onChange={(e) => editTool(t.id, { authPass: e.target.value })}
                        placeholder="Password"
                        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                    </>
                  )}
                </div>
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Parameters
                    </p>
                    <p className="text-[10px] text-slate-400">
                      What the model supplies. Use{' '}
                      <code className="rounded bg-slate-200 px-1">{'{{name}}'}</code>{' '}
                      above to place a value.
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      editTool(t.id, {
                        params: [
                          ...t.params,
                          {
                            id: uid(),
                            name: '',
                            type: 'string',
                            required: true,
                            description: '',
                          },
                        ],
                      })
                    }
                    className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium text-indigo-600 hover:bg-indigo-50"
                  >
                    <Plus size={12} /> Add
                  </button>
                </div>
                {t.params.length === 0 && (
                  <p className="text-[11px] text-slate-400">No parameters.</p>
                )}
                <div className="space-y-1.5">
                  {t.params.map((p) => (
                    <div key={p.id} className="flex gap-2">
                      <input
                        value={p.name}
                        onChange={(e) =>
                          editTool(t.id, {
                            params: t.params.map((x) =>
                              x.id === p.id ? { ...x, name: e.target.value } : x,
                            ),
                          })
                        }
                        placeholder="order_id"
                        className={`w-36 shrink-0 rounded-lg border px-3 py-2 font-mono text-sm outline-none focus:ring-1 ${
                          p.name.trim()
                            ? 'border-slate-300 focus:border-indigo-500 focus:ring-indigo-500'
                            : 'border-red-400 focus:border-red-500 focus:ring-red-500'
                        }`}
                      />
                      <select
                        value={p.type}
                        onChange={(e) =>
                          editTool(t.id, {
                            params: t.params.map((x) =>
                              x.id === p.id
                                ? { ...x, type: e.target.value as Param['type'] }
                                : x,
                            ),
                          })
                        }
                        className="w-24 shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      >
                        <option value="string">string</option>
                        <option value="number">number</option>
                        <option value="boolean">boolean</option>
                      </select>
                      <input
                        value={p.description}
                        onChange={(e) =>
                          editTool(t.id, {
                            params: t.params.map((x) =>
                              x.id === p.id
                                ? { ...x, description: e.target.value }
                                : x,
                            ),
                          })
                        }
                        placeholder="What this value is"
                        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                      <label
                        title="Required"
                        className="flex shrink-0 items-center gap-1 text-[11px] text-slate-500"
                      >
                        <input
                          type="checkbox"
                          checked={p.required}
                          onChange={(e) =>
                            editTool(t.id, {
                              params: t.params.map((x) =>
                                x.id === p.id
                                  ? { ...x, required: e.target.checked }
                                  : x,
                              ),
                            })
                          }
                          className="h-3.5 w-3.5 accent-indigo-600"
                        />
                        req
                      </label>
                      <button
                        onClick={() =>
                          editTool(t.id, {
                            params: t.params.filter((x) => x.id !== p.id),
                          })
                        }
                        className="shrink-0 rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t border-slate-200 pt-3">
                {t.params.length > 0 && (
                  <div className="mb-2 space-y-1.5">
                    <p className="text-[11px] font-medium text-slate-500">Test values</p>
                    {t.params.map((p) => (
                      <div key={p.id} className="flex items-center gap-2">
                        <span className="w-36 shrink-0 truncate font-mono text-[11px] text-slate-500">
                          {p.name || '(unnamed)'}
                        </span>
                        <input
                          value={values[t.id]?.[p.name] ?? ''}
                          onChange={(e) =>
                            setValues((v) => ({
                              ...v,
                              [t.id]: { ...v[t.id], [p.name]: e.target.value },
                            }))
                          }
                          placeholder={p.description || p.type}
                          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                        />
                      </div>
                    ))}
                  </div>
                )}
                <button
                  onClick={() => testTool(t)}
                  disabled={testing === t.id}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                >
                  <Play size={14} /> {testing === t.id ? 'Sending…' : 'Test tool'}
                </button>
                {results[t.id] && (
                  <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-900 px-3 py-2.5 font-mono text-[11px] leading-relaxed text-slate-100">
                    {results[t.id]}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
