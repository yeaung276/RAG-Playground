import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';

const SIZES = {
  sm: 'w-[90vw] max-w-md',
  md: 'w-[90vw] max-w-2xl',
  lg: 'h-[88vh] w-[94vw] max-w-6xl',
} as const;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  /** Muted line beside the title. */
  subtitle?: string;
  size?: keyof typeof SIZES;
  children: React.ReactNode;
}

export default function Modal({
  open,
  onOpenChange,
  title,
  subtitle,
  size = 'md',
  children,
}: Props) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm" />
        <Dialog.Content
          className={`fixed left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-xl bg-white shadow-xl focus:outline-none ${SIZES[size]}`}
        >
          <div className="flex items-center justify-between gap-4 border-b border-slate-200 px-5 py-3">
            <div className="flex min-w-0 items-baseline gap-2">
              <Dialog.Title className="shrink-0 text-base font-semibold text-slate-900">
                {title}
              </Dialog.Title>
              {subtitle && <span className="truncate text-xs text-slate-400">{subtitle}</span>}
            </div>
            <Dialog.Close className="shrink-0 text-slate-400 hover:text-slate-600">
              <X size={18} />
            </Dialog.Close>
          </div>

          <div className="flex min-h-0 flex-1 flex-col">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
