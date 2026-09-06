import { useEffect, useRef, useState } from 'react';
import { readFrames } from '../../api/sse';
import { useWidgetConfig } from '../config';

export type SessionStatus = 'connecting' | 'open' | 'closed';

interface Frame {
  type: string;
  data: unknown;
}

const subscribers = new Map<string, Set<(data: never) => void>>();
const statusListeners = new Set<(status: SessionStatus) => void>();

let status: SessionStatus = 'closed';
let controller: AbortController | null = null;
let consumers = 0;

function setStatus(next: SessionStatus) {
  status = next;
  statusListeners.forEach((listener) => listener(next));
}

async function connect(backendUrl: string, forceNew: boolean) {
  controller?.abort();
  const current = new AbortController();
  controller = current;
  setStatus('connecting');

  try {
    const response = await fetch(
      `${backendUrl}/api/control${forceNew ? '?new=true' : ''}`,
      { method: 'POST', credentials: 'include', signal: current.signal },
    );
    if (response.ok && response.body) {
      // Headers (incl. the session cookie) have arrived — the session is usable.
      setStatus('open');
      subscribers.get('session.open')?.forEach((handler) => handler(undefined as never));
      await readFrames<Frame>(response.body, ({ type, data }) =>
        subscribers.get(type)?.forEach((handler) => handler(data as never)),
      );
    }
  } catch {
    // aborted by restart/unmount, or the connection dropped
  }
  if (controller === current) setStatus('closed');
}

// POST /api/control sets the session cookie and holds the session open for as
// long as the response body stays open. `restart` drops it for a fresh one.
export function useSession() {
  const { backendUrl } = useWidgetConfig();
  const [current, setCurrent] = useState(status);

  useEffect(() => {
    statusListeners.add(setCurrent);
    consumers++;
    if (controller === null) void connect(backendUrl, false);

    return () => {
      statusListeners.delete(setCurrent);
      if (--consumers === 0) {
        controller?.abort();
        controller = null;
      }
    };
  }, [backendUrl]);

  return { status: current, restart: () => void connect(backendUrl, true) };
}

/** Subscribes to one control event for as long as the component is mounted. */
export function useControlEvent<T>(type: string, handler: (data: T) => void) {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    const handlers = subscribers.get(type) ?? new Set<(data: never) => void>();
    subscribers.set(type, handlers);
    const listener = (data: never) => handlerRef.current(data as T);
    handlers.add(listener);
    return () => {
      handlers.delete(listener);
    };
  }, [type]);
}
