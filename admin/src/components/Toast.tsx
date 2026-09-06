import { useSyncExternalStore } from 'react';
import * as Toast from '@radix-ui/react-toast';
import { CheckCircle2, CircleAlert, X } from 'lucide-react';

export type ToastVariant = 'error' | 'success';

interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
}

// Small queue store so non-React callers (e.g. the React Query cache's
// onError) can raise toasts; Radix owns the a11y, timing, and swipe behaviour.
let items: ToastItem[] = [];
const listeners = new Set<() => void>();
let nextId = 1;

function emit() {
  for (const l of listeners) l();
}

function remove(id: number) {
  items = items.filter((t) => t.id !== id);
  emit();
}

/** Show a transient toast. Auto-dismisses after a few seconds. */
export function pushToast(message: string, variant: ToastVariant = 'error') {
  items = [...items, { id: nextId++, message, variant }];
  emit();
}

const STYLES: Record<ToastVariant, string> = {
  error: 'bg-red-600 text-white',
  success: 'bg-emerald-600 text-white',
};

/** Renders the toast stack. Mount once, near the app root. */
export function Toaster() {
  const list = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => items,
  );

  return (
    <Toast.Provider swipeDirection="right">
      {list.map((t) => (
        <Toast.Root
          key={t.id}
          duration={5000}
          onOpenChange={(open) => !open && remove(t.id)}
          className={`toast-in flex items-start gap-2.5 rounded-lg px-4 py-3 text-sm shadow-lg ring-1 ring-black/5 ${STYLES[t.variant]}`}
        >
          {t.variant === 'success' ? (
            <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
          ) : (
            <CircleAlert size={16} className="mt-0.5 shrink-0" />
          )}
          <Toast.Description className="min-w-0 flex-1 break-words">
            {t.message}
          </Toast.Description>
          <Toast.Close
            aria-label="Dismiss"
            className="-mr-1 shrink-0 rounded p-0.5 text-white/70 hover:bg-white/20 hover:text-white"
          >
            <X size={14} />
          </Toast.Close>
        </Toast.Root>
      ))}
      <Toast.Viewport className="fixed bottom-4 right-4 z-50 flex w-full max-w-sm list-none flex-col gap-2 p-0 outline-none" />
    </Toast.Provider>
  );
}
